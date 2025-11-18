# main.py
import os
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from trading_bot_lib import BotManager  # dùng lại logic bot hiện có của bạn


# =============================
# TRẠNG THÁI HỆ THỐNG (IN-MEMORY)
# =============================

app = FastAPI(
    title="Trading Bot Backend (Web + Mobile, NO Telegram)",
    version="1.0.0",
)

# Cho phép web/app mobile gọi API (sau này có domain thì thu hẹp lại)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tạm thời cho tất cả, sau có thể sửa cho chặt
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lưu thông tin tài khoản + bot manager trong app.state
app.state.api_key: Optional[str] = None
app.state.api_secret: Optional[str] = None
app.state.bot_manager: Optional[BotManager] = None


# =============================
# HÀM TIỆN ÍCH HTML
# =============================

def html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 960px;
            margin: 0 auto;
            padding: 16px;
            background-color: #020617;
            color: #e5e7eb;
        }}
        h1, h2, h3 {{ color: #facc15; }}
        a {{ color: #38bdf8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .card {{
            background: #020617;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 16px;
            border: 1px solid #1f2937;
        }}
        .btn {{
            display: inline-block;
            padding: 8px 14px;
            border-radius: 999px;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }}
        .btn-primary {{ background: #22c55e; color: #0f172a; }}
        .btn-danger {{ background: #ef4444; color: white; }}
        .btn-secondary {{ background: #1f2937; color: #e5e7eb; }}
        form {{ margin-top: 12px; }}
        label {{ display: block; margin-top: 8px; margin-bottom: 4px; }}
        input, select {{
            width: 100%;
            padding: 6px 8px;
            border-radius: 8px;
            border: 1px solid #4b5563;
            background: #020617;
            color: #e5e7eb;
        }}
        .row {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .row > div {{
            flex: 1;
            min-width: 160px;
        }}
        small {{ color: #9ca3af; }}
        hr {{ border-color: #1f2937; margin: 24px 0; }}
        pre {{
            background: #020617;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 13px;
            white-space: pre-wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 11px;
            background: #1f2937;
            color: #e5e7eb;
        }}
    </style>
</head>
<body>
    {body}
</body>
</html>"""


# =============================
# HÀM LẤY BOT MANAGER (SAU KHI USER NHẬP API)
# =============================

def get_bot_manager() -> Optional[BotManager]:
    return app.state.bot_manager


def is_account_configured() -> bool:
    return app.state.api_key is not None and app.state.api_secret is not None and app.state.bot_manager is not None


# =============================
# WEB UI – TRANG CHÍNH
# =============================

@app.get("/", response_class=HTMLResponse)
async def index():
    # Nếu chưa cấu hình tài khoản, hiển thị form nhập API/Secret
    if not is_account_configured():
        body = """
        <h1>⚙️ Cấu hình tài khoản Binance Futures</h1>
        <div class="card">
            <h2>🔑 Nhập API Key & Secret</h2>
            <form method="post" action="/setup-account">
                <label>API Key</label>
                <input type="password" name="api_key" required>

                <label>API Secret</label>
                <input type="password" name="api_secret" required>

                <br><br>
                <button class="btn btn-primary" type="submit">Lưu & Khởi tạo Bot Manager</button>
            </form>
            <p><small>Lưu ý: API/Secret được lưu trong RAM của server (app.state), không ghi ra file.</small></p>
        </div>
        """
        return html_page("Cấu hình tài khoản", body)

    # Nếu đã cấu hình tài khoản => hiển thị dashboard bot
    bm = get_bot_manager()

    # Thống kê nhanh
    try:
        summary_text = bm.get_position_summary()
    except Exception as e:
        summary_text = f"Không lấy được thống kê: {e}"

    # Danh sách bot
    bot_rows = ""
    for bot_id, bot in bm.bots.items():
        active = len(getattr(bot, "active_symbols", []))
        max_coins = getattr(bot, "max_coins", 1)
        mode = getattr(bot, "bot_mode", "unknown")
        bot_rows += f"""
        <div class="card">
            <h3>🤖 {bot_id}</h3>
            <p>
                <span class="badge">Mode: {mode}</span>
                &nbsp;&nbsp;
                Coin đang theo dõi: <b>{active}</b> / {max_coins}
            </p>
            <form method="post" action="/stop-bot">
                <input type="hidden" name="bot_id" value="{bot_id}">
                <button class="btn btn-danger" type="submit">⛔ Dừng bot này</button>
            </form>
        </div>
        """

    if not bot_rows:
        bot_rows = "<p><small>Hiện chưa có bot nào đang chạy.</small></p>"

    body = f"""
    <h1>🤖 Trading Bot – Web UI (không dùng Telegram)</h1>
    <p>API Key/Secret đã được cấu hình. Bạn có thể tạo bot, dừng bot và xem thống kê tại đây.</p>

    <div class="card">
        <h2>📊 Thống kê nhanh</h2>
        <pre>{summary_text}</pre>
        <form method="get" action="/summary">
            <button class="btn btn-secondary" type="submit">🔄 Lấy summary dạng JSON (cho mobile/web khác)</button>
        </form>
    </div>

    <div class="card">
        <h2>➕ Tạo bot mới</h2>
        <form method="post" action="/add-bot">
            <div class="row">
                <div>
                    <label>Chế độ bot</label>
                    <select name="bot_mode">
                        <option value="static">🤖 Static – Chọn 1 coin cố định</option>
                        <option value="dynamic">🔄 Dynamic – Tự tìm coin</option>
                    </select>
                    <small>Dynamic: để trống Symbol, bot tự chọn coin theo RSI + volume.</small>
                </div>
                <div>
                    <label>Symbol (ví dụ: XRPUSDC)</label>
                    <input type="text" name="symbol" placeholder="XRPUSDC (để trống nếu Dynamic)">
                </div>
            </div>

            <div class="row">
                <div>
                    <label>Đòn bẩy (leverage)</label>
                    <input type="number" name="lev" value="10" min="1" max="125" required>
                </div>
                <div>
                    <label>% số dư cho mỗi lệnh</label>
                    <input type="number" name="percent" value="5" min="1" max="100" step="0.1" required>
                </div>
            </div>

            <div class="row">
                <div>
                    <label>TP %</label>
                    <input type="number" name="tp" value="50" min="1" step="1" required>
                </div>
                <div>
                    <label>SL % (0 = tắt SL cố định)</label>
                    <input type="number" name="sl" value="0" min="0" step="1" required>
                </div>
            </div>

            <div class="row">
                <div>
                    <label>ROI trigger % (0 = tắt)</label>
                    <input type="number" name="roi_trigger" value="0" min="0" step="1">
                </div>
                <div>
                    <label>Số coin tối đa bot quản lý</label>
                    <input type="number" name="bot_count" value="3" min="1" max="20" required>
                </div>
            </div>

            <br>
            <button class="btn btn-primary" type="submit">🚀 Tạo bot</button>
        </form>
    </div>

    <div class="card">
        <h2>📋 Danh sách bot</h2>
        {bot_rows}
        <hr>
        <form method="post" action="/stop-all-bots" style="display:inline-block;margin-right:8px;">
            <button class="btn btn-danger" type="submit">🛑 Dừng TẤT CẢ bot</button>
        </form>
        <form method="post" action="/stop-all-coins" style="display:inline-block;">
            <button class="btn btn-secondary" type="submit">⛔ Chỉ dừng toàn bộ COIN</button>
        </form>
    </div>
    """

    return html_page("Trading Bot Web UI", body)


# =============================
# WEB – CẤU HÌNH TÀI KHOẢN
# =============================

@app.post("/setup-account", response_class=HTMLResponse)
async def setup_account(
    api_key: str = Form(...),
    api_secret: str = Form(...),
):
    """
    Người dùng nhập API Key & Secret ngay trên web.
    Lưu vào app.state và khởi tạo BotManager.
    """
    api_key = api_key.strip()
    api_secret = api_secret.strip()

    app.state.api_key = api_key
    app.state.api_secret = api_secret

    # KHÔNG dùng Telegram nữa => không truyền token/chat_id
    bm = BotManager(
        api_key=api_key,
        api_secret=api_secret,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )
    app.state.bot_manager = bm

    # Sau khi cấu hình xong, quay lại /
    return RedirectResponse(url="/", status_code=303)


# =============================
# WEB – TẠO / DỪNG BOT
# =============================

@app.post("/add-bot", response_class=HTMLResponse)
async def add_bot_web(
    bot_mode: str = Form("static"),
    symbol: str = Form(""),
    lev: int = Form(...),
    percent: float = Form(...),
    tp: float = Form(...),
    sl: float = Form(...),
    roi_trigger: float = Form(0),
    bot_count: int = Form(1),
):
    if not is_account_configured():
        return RedirectResponse(url="/", status_code=303)

    bm = get_bot_manager()

    symbol_val = symbol.strip().upper() or None
    roi_val = None if roi_trigger is None or float(roi_trigger) <= 0 else float(roi_trigger)

    ok = bm.add_bot(
        symbol=symbol_val,
        lev=int(lev),
        percent=float(percent),
        tp=float(tp),
        sl=float(sl),
        roi_trigger=roi_val,
        strategy_type="Hệ-thống-RSI-Khối-lượng",
        bot_mode="dynamic" if bot_mode == "dynamic" else "static",
        bot_count=int(bot_count),
    )

    if ok:
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(
        html_page("Lỗi", "<h1>Không tạo được bot – kiểm tra API key / số dư / config.</h1><a href='/'>Quay lại</a>"),
        status_code=400,
    )


@app.post("/stop-bot", response_class=HTMLResponse)
async def stop_bot_web(bot_id: str = Form(...)):
    if is_account_configured():
        bm = get_bot_manager()
        bm.stop_bot(bot_id)
    return RedirectResponse(url="/", status_code=303)


@app.post("/stop-all-bots", response_class=HTMLResponse)
async def stop_all_bots_web():
    if is_account_configured():
        bm = get_bot_manager()
        bm.stop_all()
    return RedirectResponse(url="/", status_code=303)


@app.post("/stop-all-coins", response_class=HTMLResponse)
async def stop_all_coins_web():
    if is_account_configured():
        bm = get_bot_manager()
        bm.stop_all_coins()
    return RedirectResponse(url="/", status_code=303)


# =============================
# API JSON CHO WEB / APP MOBILE
# =============================

@app.get("/api/account-status")
async def api_account_status():
    """
    Để web/app mobile kiểm tra đã cấu hình API chưa.
    """
    return {
        "configured": is_account_configured(),
    }


@app.post("/api/setup-account")
async def api_setup_account(data: Dict[str, Any]):
    """
    API JSON: { "api_key": "...", "api_secret": "..." }
    Dùng cho app mobile / frontend JS.
    """
    api_key = data.get("api_key", "").strip()
    api_secret = data.get("api_secret", "").strip()
    if not api_key or not api_secret:
        return JSONResponse({"ok": False, "error": "Thiếu api_key hoặc api_secret"}, status_code=400)

    app.state.api_key = api_key
    app.state.api_secret = api_secret

    bm = BotManager(
        api_key=api_key,
        api_secret=api_secret,
        telegram_bot_token=None,
        telegram_chat_id=None,
    )
    app.state.bot_manager = bm

    return {"ok": True}


@app.get("/api/summary")
async def api_summary():
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()
    try:
        text = bm.get_position_summary()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "summary": text}


@app.get("/api/bots")
async def api_bots():
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()
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
async def api_add_bot(data: Dict[str, Any]):
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()

    bot_mode = data.get("bot_mode", "static")
    symbol = data.get("symbol") or ""
    lev = int(data.get("lev", 10))
    percent = float(data.get("percent", 5))
    tp = float(data.get("tp", 50))
    sl = float(data.get("sl", 0))
    roi_trigger = float(data.get("roi_trigger", 0))
    bot_count = int(data.get("bot_count", 1))

    symbol_val = symbol.strip().upper() or None
    roi_val = None if roi_trigger <= 0 else roi_trigger

    ok = bm.add_bot(
        symbol=symbol_val,
        lev=lev,
        percent=percent,
        tp=tp,
        sl=sl,
        roi_trigger=roi_val,
        strategy_type="Hệ-thống-RSI-Khối-lượng",
        bot_mode="dynamic" if bot_mode == "dynamic" else "static",
        bot_count=bot_count,
    )

    return {"ok": bool(ok)}


@app.post("/api/stop-bot")
async def api_stop_bot(data: Dict[str, Any]):
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()
    bot_id = data.get("bot_id")
    if not bot_id:
        return JSONResponse({"ok": False, "error": "Thiếu bot_id"}, status_code=400)

    bm.stop_bot(bot_id)
    return {"ok": True}


@app.post("/api/stop-all-bots")
async def api_stop_all_bots():
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()
    bm.stop_all()
    return {"ok": True}


@app.post("/api/stop-all-coins")
async def api_stop_all_coins():
    if not is_account_configured():
        return JSONResponse({"ok": False, "error": "Chưa cấu hình tài khoản"}, status_code=400)

    bm = get_bot_manager()
    bm.stop_all_coins()
    return {"ok": True}


# =============================
# CHẠY LOCAL
# =============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
