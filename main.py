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
            backgrou8080, reload=True)
