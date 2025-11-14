import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Bot System", version="1.0.0")

# CORS middleware - QUAN TRỌNG
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tạo thư mục static nếu chưa tồn tại
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class UserCredentials(BaseModel):
    api_key: str
    api_secret: str

class BotConfig(BaseModel):
    symbol: Optional[str] = None
    lev: int
    percent: float
    tp: float
    sl: float
    roi_trigger: Optional[float] = None
    bot_mode: str = "static"
    bot_count: int = 1

# Health check endpoint - QUAN TRỌNG
@app.get("/")
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Bot System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 50px;
                margin: 0;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            .status {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                margin: 20px 0;
                backdrop-filter: blur(10px);
            }
            .btn {
                background: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Trading Bot System</h1>
            <div class="status">
                <h2>✅ Backend Server is Running!</h2>
                <p>Ứng dụng đã được khởi động thành công trên Railway.</p>
                <p>Phiên bản: FastAPI + PWA Ready</p>
            </div>
            <div>
                <a href="/app" class="btn">🚀 Mở Ứng Dụng</a>
                <a href="/health" class="btn">❤️ Health Check</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "service": "trading-bot-api"})

@app.get("/app")
async def serve_app():
    """Serve the main application"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
            <body>
                <h1>App Interface</h1>
                <p>Frontend will be loaded here. Make sure static/index.html exists.</p>
            </body>
        </html>
        """)

# API endpoints
@app.post("/api/connect")
async def connect_binance(credentials: UserCredentials):
    try:
        # Test mode - sẽ tích hợp với bot_core sau
        return JSONResponse({
            "success": True,
            "message": "Kết nối thành công! (Test Mode)",
            "balance": 1000.0,
            "test_mode": True
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Lỗi kết nối: {str(e)}"
        })

@app.get("/api/system-info")
async def get_system_info():
    return JSONResponse({
        "balance": 1000.0,
        "total_bots": 0,
        "searching_bots": 0,
        "waiting_bots": 0,
        "trading_bots": 0,
        "total_long_count": 0,
        "total_short_count": 0,
        "total_long_pnl": 0,
        "total_short_pnl": 0,
        "total_unrealized_pnl": 0,
        "test_mode": True
    })

@app.get("/api/bots")
async def get_bots():
    return JSONResponse([])

@app.post("/api/add-bot")
async def add_bot(config: BotConfig):
    return JSONResponse({
        "success": True,
        "message": "Bot added successfully (Test Mode)"
    })

@app.post("/api/stop-bot")
async def stop_bot():
    return JSONResponse({
        "success": True,
        "message": "Bot stopped successfully (Test Mode)"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
