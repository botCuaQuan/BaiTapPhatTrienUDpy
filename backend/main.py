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

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import secrets

# 🚨 BotManager (fake nếu chưa có bot thực)
try:
    from trading_bot_lib import BotManager
except ImportError:
    class BotManager:
        def __init__(self, *a, **k): pass
        def add_bot(self, **k): pass
        def stop_bot(self, bot_id): pass
        def stop_all_bots(self): pass


# ================ DATABASE =================
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)


class BotConfig(Base):
    __tablename__ = "bot_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    bot_mode = Column(String(20), nullable=False)
    symbol = Column(String(50), nullable=True)
    lev = Column(Integer, nullable=False)
    percent = Column(Float, nullable=False)
    tp = Column(Float, nullable=False)
    sl = Column(Float, nullable=False)
    roi_trigger = Column(Float, nullable=True)
    bot_count = Column(Integer, nullable=False, default=1)


Base.metadata.create_all(bind=engine)

# ================ FASTAPI APP =================
app = FastAPI(title="Quan Trading Backend", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ================ DB DEPENDENCY ================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================ AUTH SYSTEM =================
TOKEN_STORE: Dict[str, int] = {}

def create_token(uid: int):
    token = secrets.token_hex(32)
    TOKEN_STORE[token] = uid
    return token

async def get_current_user(
    x_auth_token: str = Header(..., alias="X-Auth-Token"),
    db: Session = Depends(get_db),
):
    uid = TOKEN_STORE.get(x_auth_token)
    if not uid:
        raise HTTPException(401, "Token hết hạn hoặc không hợp lệ")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(401, "User không tồn tại")
    return user


# ================ SCHEMAS =================
class RegisterReq(BaseModel):   username: str; password: str
class LoginReq(BaseModel):      username: str; password: str
class SetupReq(BaseModel):      api_key: str; api_secret: str
class SetSymbolReq(BaseModel):  symbol: str
class AddBotReq(BaseModel):
    bot_mode: str = "static"
    symbol: Optional[str] = None
    lev: int = 10
    percent: float = 5
    tp: float = 50
    sl: float = 0
    roi_trigger: float = 0
    bot_count: int = 1
class StopBotReq(BaseModel):    bot_id: int


# ================ BOT STORE =================
BOT_MANAGERS: Dict[int, BotManager] = {}
SYMBOL_STORE: Dict[int, str] = {}   # user_id -> symbol

def restore_bots(user: User, bm: BotManager, db: Session):
    cfgs = db.query(BotConfig).filter(BotConfig.user_id == user.id).all()
    for cfg in cfgs:
        bm.add_bot(
            symbol=cfg.symbol, lev=cfg.lev, percent=cfg.percent,
            tp=cfg.tp, sl=cfg.sl, roi_trigger=cfg.roi_trigger,
            bot_mode=cfg.bot_mode, bot_count=cfg.bot_count,
            strategy_type="RSI-volume-auto"
        )


def get_bm(user: User, db: Session):
    bm = BOT_MANAGERS.get(user.id)
    if bm is None:
        if not (user.api_key and user.api_secret):
            raise HTTPException(400, "Chưa cấu hình API Binance")
        bm = BotManager(api_key=user.api_key, api_secret=user.api_secret)
        BOT_MANAGERS[user.id] = bm
        restore_bots(user, bm, db)
    return bm


# ================ AUTH API ================
@app.post("/api/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "Username đã tồn tại")
    u = User(username=req.username, password=req.password)
    db.add(u); db.commit(); db.refresh(u)
    return {"token": create_token(u.id), "username": u.username}

@app.post("/api/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == req.username,
                              User.password == req.password).first()
    if not u: raise HTTPException(401, "Sai username/password")
    return {"token": create_token(u.id), "username": u.username}


# ================ ACCOUNT API ================
@app.get("/api/account-status")
def acc_status(u: User = Depends(get_current_user)):
    return {"configured": bool(u.api_key and u.api_secret)}

@app.post("/api/setup-account")
def setup_acc(req: SetupReq, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    u.api_key = req.api_key; u.api_secret = req.api_secret
    db.add(u); db.commit()
    return {"ok": True}

@app.post("/api/set-symbol")
def set_symbol(req: SetSymbolReq, u: User = Depends(get_current_user)):
    SYMBOL_STORE[u.id] = req.symbol.upper()
    return {"symbol": SYMBOL_STORE[u.id], "ok": True}


# ================ BOT API ================
@app.get("/api/summary")
def summary(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfgs = db.query(BotConfig).filter(BotConfig.user_id == u.id).all()
    lines = [f"Số bot: {len(cfgs)}"]
    for c in cfgs: lines.append(f"- Bot {c.id}: {c.bot_mode}, {c.symbol}")
    return {"summary": "\n".join(lines)}

@app.get("/api/bots")
def bots(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfgs = db.query(BotConfig).filter(BotConfig.user_id == u.id).all()
    return {"bots": [{
        "bot_id": c.id, "mode": c.bot_mode, "symbol": c.symbol,
        "lev": c.lev, "percent": c.percent, "tp": c.tp, "sl": c.sl,
        "roi_trigger": c.roi_trigger, "bot_count": c.bot_count,
        "active_coins": 0, "max_coins": c.bot_count
    } for c in cfgs]}

@app.post("/api/add-bot")
def add_bot(req: AddBotReq, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = BotConfig(
        user_id=u.id, bot_mode=req.bot_mode, symbol=req.symbol,
        lev=req.lev, percent=req.percent, tp=req.tp, sl=req.sl,
        roi_trigger=req.roi_trigger if req.roi_trigger>0 else None,
        bot_count=req.bot_count
    )
    db.add(c); db.commit(); db.refresh(c)
    try:
        bm = get_bm(u, db)
        bm.add_bot(symbol=req.symbol, lev=req.lev, percent=req.percent,
                   tp=req.tp, sl=req.sl, roi_trigger=req.roi_trigger,
                   bot_mode=req.bot_mode, bot_count=req.bot_count,
                   strategy_type="RSI-volume-auto")
    except: pass
    return {"ok": True}

@app.post("/api/stop-bot")
def stop_bot(req: StopBotReq, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(BotConfig).filter(BotConfig.id==req.bot_id,
                                   BotConfig.user_id==u.id).first()
    if not c: raise HTTPException(404, "Bot không tồn tại")
    try:
        get_bm(u, db).stop_bot(c.id)
    except: pass
    db.delete(c); db.commit(); return {"ok": True}


# ================ REALTIME WS =================
@app.websocket("/ws/prices")
async def ws_prices(ws: WebSocket):
    await ws.accept()
    price, balance, pnl = 65000, 1000, 0

    try:
        while True:
            price += random.uniform(-30, 30)
            balance += random.uniform(-2, 2)
            pnl += random.uniform(-4, 4)

            data = {
                "symbol": "BTCUSDT",
                "price": round(price, 2),
                "volume": round(random.uniform(10, 80), 2),
                "balance": round(balance, 2),
                "pnl": round(pnl, 2),
                "bot_running": random.randint(0, 3),
                "timestamp": int(time.time())
            }
            await ws.send_json(data)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("WS client disconnected")
    except Exception as e:
        print("WS error:", e)


# ⚠️ STATIC FILE PHẢI ĐỂ CUỐI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# RUN
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
