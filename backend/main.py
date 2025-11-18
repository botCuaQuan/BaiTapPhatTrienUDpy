# main.py
import os
import secrets
import hashlib
import asyncio
import time
import random
from typing import Optional, Dict, Tuple, Any

from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,   # <- THÊM
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from trading_bot_lib import BotManager  # file bot của bạn


# =========================
# CẤU HÌNH DATABASE
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Cho dev local: nếu chưa set DATABASE_URL thì dùng SQLite
    DATABASE_URL = "sqlite:///./local_dev.db"

# Railway Postgres thường có format: postgresql://...
# SQLAlchemy khuyến nghị dùng postgresql+psycopg2://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)


class BotConfig(Base):
    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    bot_mode = Column(String(20), nullable=False)    # "static" / "dynamic"
    symbol = Column(String(50), nullable=True)
    lev = Column(Integer, nullable=False)
    percent = Column(Float, nullable=False)
    tp = Column(Float, nullable=False)
    sl = Column(Float, nullable=False)
    roi_trigger = Column(Float, nullable=True)
    bot_count = Column(Integer, nullable=False, default=1)

Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# APP & CORS & STATIC FRONTEND
# =========================

app = FastAPI(
    title="Trading Bot Backend (Multi-user, DB on Railway)",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sau này muốn thì siết lại domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend (web) từ thư mục "frontend"
# Cấu trúc repo:
#   main.py
#   trading_bot_lib.py
#   requirements.txt
#   Procfile
#   frontend/
#       index.html
#       app.js
#       style.css

# =========================
# LƯU SESSION + BOTMANAGER TRONG RAM
# =========================

# sessions[token] = user_id
app.state.sessions: Dict[str, int] = {}

# bot_managers[user_id] = BotManager(...)
app.state.bot_managers: Dict[int, BotManager] = {}


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def verify_password(pw: str, pw_hash: str) -> bool:
    return hash_password(pw) == pw_hash


def create_token() -> str:
    return secrets.token_hex(32)


def get_session_store() -> Dict[str, int]:
    return app.state.sessions


def get_bot_manager_store() -> Dict[int, BotManager]:
    return app.state.bot_managers

def restore_bots_from_db(user: User, bm: BotManager):
    """
    Đọc các cấu hình bot trong DB cho user và add lại vào BotManager.
    Mục tiêu: khi deploy lên chương trình khác, chỉ cần cùng DB là bot được khởi tạo lại.
    """
    db = SessionLocal()
    try:
        configs = db.query(BotConfig).filter(BotConfig.user_id == user.id).all()
        for cfg in configs:
            try:
                bm.add_bot(
                    symbol=cfg.symbol,
                    lev=cfg.lev,
                    percent=cfg.percent,
                    tp=cfg.tp,
                    sl=cfg.sl,
                    roi_trigger=cfg.roi_trigger,
                    strategy_type="Hệ-thống-RSI-Khối-lượng",
                    bot_mode=cfg.bot_mode,
                    bot_count=cfg.bot_count,
                )
            except Exception:
                # Nếu có cấu hình cũ không còn phù hợp nữa thì bỏ qua
                continue
    finally:
        db.close()

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupAccountRequest(BaseModel):
    api_key: str
    api_secret: str


class AddBotRequest(BaseModel):
    bot_mode: str = "static"   # "static" | "dynamic"
    symbol: Optional[str] = ""
    lev: int = 10
    percent: float = 5.0
    tp: float = 50.0
    sl: float = 0.0
    roi_trigger: float = 0.0
    bot_count: int = 1


class StopBotRequest(BaseModel):
    bot_id: str


# =========================
# AUTH HELPER: LẤY USER HIỆN TẠI TỪ TOKEN
# =========================

async def get_current_user(
    x_auth_token: str = Header(None, alias="X-Auth-Token"),
    db: Session = Depends(get_db),
) -> Tuple[int, User]:
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    sessions = get_session_store()
    user_id = sessions.get(x_auth_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid auth token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user_id, user


# =========================
# API: TÀI KHOẢN (REGISTER / LOGIN / ME)
# =========================

@app.post("/api/register")
async def api_register(data: RegisterRequest, db: Session = Depends(get_db)):
    username = data.username.strip()
    password = data.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    user = User(
        username=username,
        password_hash=hash_password(password),
        api_key=None,
        api_secret=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token()
    sessions = get_session_store()
    sessions[token] = user.id

    return {"ok": True, "token": token, "username": user.username}


@app.post("/api/login")
async def api_login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username.strip()
    password = data.password

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Sai username hoặc password")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Sai username hoặc password")

    token = create_token()
    sessions = get_session_store()
    sessions[token] = user.id

    return {"ok": True, "token": token, "username": user.username}


@app.get("/api/me")
async def api_me(current=Depends(get_current_user)):
    user_id, user = current
    has_api = bool(user.api_key and user.api_secret)
    return {
        "ok": True,
        "user_id": user_id,
        "username": user.username,
        "has_api": has_api,
    }


# =========================
# HỖ TRỢ LẤY / TẠO BOTMANAGER THEO USER
# =========================

def get_or_create_bot_manager_for_user(user: User) -> BotManager:
    bm_store = get_bot_manager_store()
    bm = bm_store.get(user.id)
    if bm is None:
        if not (user.api_key and user.api_secret):
            raise HTTPException(status_code=400, detail="User chưa cấu hình API Binance")
        bm = BotManager(
            api_key=user.api_key,
            api_secret=user.api_secret,
            telegram_bot_token=None,
            telegram_chat_id=None,
        )
        bm_store[user.id] = bm

        # 🔁 Khôi phục lại các bot từ DB
        restore_bots_from_db(user, bm)

    return bm



# =========================
# API: CẤU HÌNH TÀI KHOẢN BINANCE
# =========================

@app.get("/api/account-status")
async def api_account_status(current=Depends(get_current_user)):
    _, user = current
    configured = bool(user.api_key and user.api_secret)
    return {"ok": True, "configured": configured}


@app.post("/api/setup-account")
async def api_setup_account(
    data: SetupAccountRequest,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id, user = current

    api_key = data.api_key.strip()
    api_secret = data.api_secret.strip()
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Thiếu api_key hoặc api_secret")

    # Lưu vào DB
    user.api_key = api_key
    user.api_secret = api_secret
    db.add(user)
    db.commit()
    db.refresh(user)

    # Khởi tạo BotManager mới và gán vào RAM
    bm_store = get_bot_manager_store()
    bm_store[user_id] = BotManager(
        api_key=api_key,
        api_secret=api_secret,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )

    return {"ok": True}


# =========================
# API: BOT – SUMMARY / LIST / ADD / STOP
# =========================

@app.get("/api/summary")
async def api_summary(current=Depends(get_current_user)):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)
    try:
        text = bm.get_position_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "summary": text}


@app.get("/api/bots")
async def api_bots(current=Depends(get_current_user)):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)

    data = []
    for bot_id, bot in bm.bots.items():
        data.append({
            "bot_id": bot_id,
            "active_coins": len(getattr(bot, "active_symbols", [])),
            "max_coins": getattr(bot, "max_coins", 1),
            "mode": getattr(bot, "bot_mode", "unknown"),
        })
    return {"ok": True, "bots": data}


@app.post("/api/add-bot")
async def api_add_bot(
    payload: AddBotRequest,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)

    symbol_val = (payload.symbol or "").strip().upper() or None
    roi_val = None if payload.roi_trigger <= 0 else payload.roi_trigger
    bot_mode = "dynamic" if payload.bot_mode == "dynamic" else "static"

    ok = bm.add_bot(
        symbol=symbol_val,
        lev=payload.lev,
        percent=payload.percent,
        tp=payload.tp,
        sl=payload.sl,
        roi_trigger=roi_val,
        strategy_type="Hệ-thống-RSI-Khối-lượng",
        bot_mode=bot_mode,
        bot_count=payload.bot_count,
    )

    # Lưu cấu hình bot vào DB để sau này khôi phục
    if ok:
        cfg = BotConfig(
            user_id=user.id,
            bot_mode=bot_mode,
            symbol=symbol_val,
            lev=payload.lev,
            percent=payload.percent,
            tp=payload.tp,
            sl=payload.sl,
            roi_trigger=roi_val,
            bot_count=payload.bot_count,
        )
        db.add(cfg)
        db.commit()

    return {"ok": bool(ok)}


@app.post("/api/stop-bot")
async def api_stop_bot(
    data: StopBotRequest,
    current=Depends(get_current_user),
):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)
    bm.stop_bot(data.bot_id)
    return {"ok": True}


@app.post("/api/stop-all-bots")
async def api_stop_all_bots(current=Depends(get_current_user)):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)
    bm.stop_all()
    return {"ok": True}


@app.post("/api/stop-all-coins")
async def api_stop_all_coins(current=Depends(get_current_user)):
    _, user = current
    bm = get_or_create_bot_manager_for_user(user)
    bm.stop_all_coins()
    return {"ok": True}

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket fake price (demo). Sau này bạn chỉ cần thay phần random
    bằng dữ liệu Binance là xong.
    """
    await websocket.accept()
    try:
        price = 65000.0
        while True:
            delta = random.uniform(-50, 50)
            price = max(1, price + delta)

            data = {
                "symbol": "BTCUSDT",
                "price": round(price, 2),
                "change": round(delta, 2),
                "volume": round(random.uniform(10, 100), 2),
                "timestamp": int(time.time()),
            }

            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected /ws/prices")

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend",
)

# =========================
# Chạy local
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
