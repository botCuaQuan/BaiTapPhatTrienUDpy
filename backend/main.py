# backend/main.py
import asyncio
import random
import time
from typing import Dict, Optional

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import secrets

# ====== IMPORT BOT MANAGER (file của bạn) ======
from trading_bot_lib import BotManager  # đảm bảo file này nằm cùng thư mục main.py


# ================== DB SETUP ==================
DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)


class BotConfig(Base):
    """
    Lưu cấu hình bot theo từng user.
    Dùng để khôi phục bot khi chuyển sang chương trình khác / server khác.
    """
    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    bot_mode = Column(String(20), nullable=False)  # "static" / "dynamic"
    symbol = Column(String(50), nullable=True)
    lev = Column(Integer, nullable=False)
    percent = Column(Float, nullable=False)
    tp = Column(Float, nullable=False)
    sl = Column(Float, nullable=False)
    roi_trigger = Column(Float, nullable=True)
    bot_count = Column(Integer, nullable=False, default=1)


Base.metadata.create_all(bind=engine)


# ================== FASTAPI APP ==================
app = FastAPI(title="Quan Trading Backend", version="1.0.0")

# CORS cho phép frontend (nếu deploy chéo domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # có thể đổi lại cho chặt hơn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend (index.html, app.js, style.css)
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend",
)


# ================== DEPENDENCY DB ==================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================== AUTH TOKEN STORE ==================
# Lưu token trong RAM: token -> user_id
TOKEN_STORE: Dict[str, int] = {}


def create_token_for_user(user_id: int) -> str:
    token = secrets.token_hex(32)
    TOKEN_STORE[token] = user_id
    return token


async def get_current_user(
    x_auth_token: str = Header(..., alias="X-Auth-Token"),
    db: Session = Depends(get_db),
) -> User:
    user_id = TOKEN_STORE.get(x_auth_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User không tồn tại.")
    return user


# ================== BOT MANAGER STORE ==================
BOT_MANAGERS: Dict[int, BotManager] = {}


def restore_bots_from_db(user: User, bm: BotManager, db: Session) -> None:
    """
    Khôi phục các bot đã lưu trong bảng BotConfig cho user.
    """
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
        except Exception as e:
            # Không để hỏng toàn bộ chỉ vì 1 cấu hình lỗi
            print(f"[restore_bots_from_db] Lỗi add_bot: {e}")


def get_bot_manager_for_user(user: User, db: Session) -> BotManager:
    """
    Lấy BotManager cho user; nếu chưa có thì tạo mới + khôi phục từ DB.
    """
    bm = BOT_MANAGERS.get(user.id)
    if bm is None:
        if not (user.api_key and user.api_secret):
            raise HTTPException(
                status_code=400,
                detail="User chưa cấu hình API Binance. Gọi /api/setup-account trước.",
            )
        bm = BotManager(
            api_key=user.api_key,
            api_secret=user.api_secret,
            telegram_bot_token=None,
            telegram_chat_id=None,
        )
        BOT_MANAGERS[user.id] = bm
        restore_bots_from_db(user, bm, db)
    return bm


# ================== Pydantic MODELS ==================
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupAccountRequest(BaseModel):
    api_key: str
    api_secret: str


class AccountStatusResponse(BaseModel):
    configured: bool


class AddBotRequest(BaseModel):
    bot_mode: str = Field(default="static")  # "static" / "dynamic"
    symbol: Optional[str] = None
    lev: int = 10
    percent: float = 5
    tp: float = 50
    sl: float = 0
    roi_trigger: float = 0
    bot_count: int = 1


class StopBotRequest(BaseModel):
    bot_id: int


# ================== AUTH APIs ==================
@app.post("/api/register")
def api_register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password.")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại.")

    user = User(username=username, password=payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token_for_user(user.id)
    return {"token": token, "username": user.username}


@app.post("/api/login")
def api_login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password.")

    user = (
        db.query(User)
        .filter(User.username == username, User.password == payload.password)
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Sai username hoặc password.")

    token = create_token_for_user(user.id)
    return {"token": token, "username": user.username}


# ================== ACCOUNT SETUP APIs ==================
@app.get("/api/account-status", response_model=AccountStatusResponse)
def api_account_status(current_user: User = Depends(get_current_user)):
    configured = bool(current_user.api_key and current_user.api_secret)
    return AccountStatusResponse(configured=configured)


@app.post("/api/setup-account")
def api_setup_account(
    payload: SetupAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.api_key = payload.api_key.strip()
    current_user.api_secret = payload.api_secret.strip()
    db.add(current_user)
    db.commit()
    return {"ok": True}


# ================== BOT APIs ==================
@app.get("/api/summary")
def api_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Summary đơn giản dựa trên các cấu hình bot đã lưu.
    Có thể thay bằng hàm summary thật của BotManager nếu bạn muốn.
    """
    configs = db.query(BotConfig).filter(BotConfig.user_id == current_user.id).all()

    lines = [f"Số bot đã cấu hình: {len(configs)}"]
    for cfg in configs:
        mode = cfg.bot_mode
        sym = cfg.symbol or "(Dynamic – auto chọn coin)"
        lines.append(
            f"- Bot #{cfg.id}: mode={mode}, symbol={sym}, lev={cfg.lev}, "
            f"%={cfg.percent}, tp={cfg.tp}, sl={cfg.sl}, "
            f"roi_trigger={cfg.roi_trigger}, count={cfg.bot_count}"
        )

    summary_text = "\n".join(lines)
    return {"summary": summary_text}


@app.get("/api/bots")
def api_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách bot dựa trên bảng BotConfig.
    UI sẽ hiển thị theo cấu hình này.
    """
    configs = db.query(BotConfig).filter(BotConfig.user_id == current_user.id).all()

    bots = []
    for cfg in configs:
        bots.append(
            {
                "bot_id": cfg.id,
                "mode": cfg.bot_mode,
                "symbol": cfg.symbol,
                "lev": cfg.lev,
                "percent": cfg.percent,
                "tp": cfg.tp,
                "sl": cfg.sl,
                "roi_trigger": cfg.roi_trigger,
                "bot_count": cfg.bot_count,
                "active_coins": 0,  # nếu muốn có số coin đang chạy thực tế, đọc từ BotManager
                "max_coins": cfg.bot_count,
            }
        )
    return {"bots": bots}


@app.post("/api/add-bot")
def api_add_bot(
    payload: AddBotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    - Gọi BotManager.add_bot để bot bắt đầu chạy.
    - Đồng thời lưu cấu hình vào DB (BotConfig) để sau này khôi phục.
    """
    symbol_val = (payload.symbol or "").strip().upper() or None
    roi_val = None if payload.roi_trigger <= 0 else payload.roi_trigger
    bot_mode = "dynamic" if payload.bot_mode == "dynamic" else "static"

    # Gọi bot manager (best-effort)
    ok = True
    try:
        bm = get_bot_manager_for_user(current_user, db)
        if hasattr(bm, "add_bot"):
            bm.add_bot(
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
    except Exception as e:
        print("[api_add-bot] Lỗi gọi BotManager.add_bot:", e)
        ok = False

    # Lưu cấu hình vào DB
    cfg = BotConfig(
        user_id=current_user.id,
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
    db.refresh(cfg)

    return {"ok": ok, "config_id": cfg.id}


@app.post("/api/stop-all-bots")
def api_stop_all_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    - Gọi BotManager dừng tất cả bot đang chạy.
    - Xóa hết cấu hình bot của user trong DB.
    """
    try:
        bm = get_bot_manager_for_user(current_user, db)
        if hasattr(bm, "stop_all_bots"):
            bm.stop_all_bots()
    except Exception as e:
        print("[api_stop-all-bots] Lỗi gọi BotManager.stop_all_bots:", e)

    db.query(BotConfig).filter(BotConfig.user_id == current_user.id).delete()
    db.commit()
    return {"ok": True}


@app.post("/api/stop-all-coins")
def api_stop_all_coins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dừng toàn bộ COIN (tùy cách bạn cài `BotManager.stop_all_coins`).
    """
    try:
        bm = get_bot_manager_for_user(current_user, db)
        if hasattr(bm, "stop_all_coins"):
            bm.stop_all_coins()
        elif hasattr(bm, "stop_all_bots"):
            # fallback
            bm.stop_all_bots()
    except Exception as e:
        print("[api_stop-all-coins] Lỗi gọi BotManager:", e)

    return {"ok": True}


@app.post("/api/stop-bot")
def api_stop_bot(
    payload: StopBotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dừng 1 bot theo config_id (bot_id).
    """
    cfg = (
        db.query(BotConfig)
        .filter(
            BotConfig.id == payload.bot_id,
            BotConfig.user_id == current_user.id,
        )
        .first()
    )
    if not cfg:
        raise HTTPException(status_code=404, detail="Bot không tồn tại.")

    # Gọi BotManager.stop_bot nếu có
    try:
        bm = get_bot_manager_for_user(current_user, db)
        if hasattr(bm, "stop_bot"):
            bm.stop_bot(cfg.id)
    except Exception as e:
        print("[api_stop-bot] Lỗi gọi BotManager.stop_bot:", e)

    db.delete(cfg)
    db.commit()
    return {"ok": True}


# ================== WEBSOCKET FAKE PRICE ==================
@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket fake dữ liệu giá để test giao diện.
    Nếu muốn dùng dữ liệu Binance thật, bạn chỉnh lại đoạn loop bên dưới.
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
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        print("Client disconnected: /ws/prices")
    except Exception as e:
        print(f"[ws/prices] Error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


# ================== MAIN ==================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
