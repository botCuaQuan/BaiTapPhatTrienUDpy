# main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Tuple, Any
import secrets
import hashlib

from trading_bot_lib import BotManager  # file bot của bạn


app = FastAPI(
    title="Trading Bot Backend (Multi-user, Web + Mobile)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # sau muốn siết lại domain web/app thì sửa chỗ này
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# LƯU USER / SESSION TRONG RAM
# =========================

# users[username] = {
#   "password_hash": str,
#   "api_key": Optional[str],
#   "api_secret": Optional[str],
#   "bot_manager": Optional[BotManager],
# }
app.state.users: Dict[str, Dict[str, Any]] = {}

# sessions[token] = username
app.state.sessions: Dict[str, str] = {}


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def verify_password(pw: str, pw_hash: str) -> bool:
    return hash_password(pw) == pw_hash


def create_token() -> str:
    return secrets.token_hex(32)


def get_user_store() -> Dict[str, Dict[str, Any]]:
    return app.state.users


def get_session_store() -> Dict[str, str]:
    return app.state.sessions


# =========================
# Pydantic models
# =========================

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
# Auth helper – lấy user hiện tại từ token
# =========================

async def get_current_user(
    x_auth_token: str = Header(None, alias="X-Auth-Token")
) -> Tuple[str, Dict[str, Any]]:
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    sessions = get_session_store()
    users = get_user_store()

    username = sessions.get(x_auth_token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid auth token")

    user = users.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return username, user


# =========================
# API: TÀI KHOẢN (REGISTER / LOGIN / ME)
# =========================

@app.post("/api/register")
async def api_register(data: RegisterRequest):
    users = get_user_store()
    username = data.username.strip()
    password = data.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password")

    if username in users:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    users[username] = {
        "password_hash": hash_password(password),
        "api_key": None,
        "api_secret": None,
        "bot_manager": None,
    }

    # Đăng nhập luôn sau khi đăng ký
    token = create_token()
    sessions = get_session_store()
    sessions[token] = username

    return {"ok": True, "token": token, "username": username}


@app.post("/api/login")
async def api_login(data: LoginRequest):
    users = get_user_store()
    username = data.username.strip()
    password = data.password

    user = users.get(username)
    if not user:
        raise HTTPException(status_code=400, detail="Sai username hoặc password")

    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Sai username hoặc password")

    token = create_token()
    sessions = get_session_store()
    sessions[token] = username

    return {"ok": True, "token": token, "username": username}


@app.get("/api/me")
async def api_me(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    has_api = bool(user.get("api_key") and user.get("api_secret") and bm is not None)
    return {
        "ok": True,
        "username": username,
        "has_api": has_api,
    }


# =========================
# API: CẤU HÌNH TÀI KHOẢN BINANCE (API KEY/SECRET)
# =========================

@app.get("/api/account-status")
async def api_account_status(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    configured = bool(user.get("api_key") and user.get("api_secret") and bm is not None)
    return {"ok": True, "configured": configured}


@app.post("/api/setup-account")
async def api_setup_account(
    data: SetupAccountRequest,
    current=Depends(get_current_user),
):
    username, user = current

    api_key = data.api_key.strip()
    api_secret = data.api_secret.strip()
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Thiếu api_key hoặc api_secret")

    bm = BotManager(
        api_key=api_key,
        api_secret=api_secret,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )

    user["api_key"] = api_key
    user["api_secret"] = api_secret
    user["bot_manager"] = bm

    return {"ok": True}


# =========================
# API: BOT – SUMMARY / LIST / ADD / STOP
# =========================

@app.get("/api/summary")
async def api_summary(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

    try:
        text = bm.get_position_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True, "summary": text}


@app.get("/api/bots")
async def api_bots(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

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
):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

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

    return {"ok": bool(ok)}


@app.post("/api/stop-bot")
async def api_stop_bot(
    data: StopBotRequest,
    current=Depends(get_current_user),
):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

    bm.stop_bot(data.bot_id)
    return {"ok": True}


@app.post("/api/stop-all-bots")
async def api_stop_all_bots(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

    bm.stop_all()
    return {"ok": True}


@app.post("/api/stop-all-coins")
async def api_stop_all_coins(current=Depends(get_current_user)):
    username, user = current
    bm: Optional[BotManager] = user.get("bot_manager")
    if bm is None:
        raise HTTPException(status_code=400, detail="Tài khoản chưa cấu hình API Binance")

    bm.stop_all_coins()
    return {"ok": True}


# =========================
# Chạy local
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
