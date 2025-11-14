import os
import json
import asyncio
import logging
from typing import Dict, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from bot_core import BotManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Bot System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active connections and bot managers
active_connections: Dict[str, WebSocket] = {}
user_bot_managers: Dict[str, BotManager] = {}

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

class StopBotRequest(BaseModel):
    bot_id: str

# Tạo thư mục static nếu chưa tồn tại
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Trang chủ với form đăng nhập"""
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading Bot System</title>
        
        <!-- PWA Meta Tags -->
        <meta name="theme-color" content="#764ba2">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="TradingBot">
        <link rel="manifest" href="/static/manifest.json">
        <link rel="apple-touch-icon" href="/static/icon-192.png">
        
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 400px;
                margin: 0 auto;
            }
            
            .header {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 30px 20px;
                margin-bottom: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                text-align: center;
            }
            
            .header h1 {
                color: white;
                margin-bottom: 10px;
                font-size: 28px;
            }
            
            .header p {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
            }
            
            .login-form {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 25px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                color: white;
                margin-bottom: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            
            .form-control:focus {
                outline: none;
                border-color: #667eea;
                background: rgba(255, 255, 255, 0.15);
            }
            
            .form-control::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            
            .btn {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
                width: 100%;
                margin-top: 10px;
            }
            
            .btn:hover {
                background: #45a049;
                transform: translateY(-2px);
            }
            
            .btn:active {
                transform: translateY(0);
            }
            
            .hidden {
                display: none;
            }
            
            .message {
                padding: 12px;
                border-radius: 8px;
                margin-top: 15px;
                text-align: center;
                font-size: 14px;
            }
            
            .success {
                background: rgba(76, 175, 80, 0.2);
                color: #4CAF50;
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            
            .error {
                background: rgba(244, 67, 54, 0.2);
                color: #f44336;
                border: 1px solid rgba(244, 67, 54, 0.3);
            }
            
            .loading {
                background: rgba(255, 193, 7, 0.2);
                color: #ffc107;
                border: 1px solid rgba(255, 193, 7, 0.3);
            }
            
            .logo {
                font-size: 48px;
                margin-bottom: 15px;
            }
            
            .info-text {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                text-align: center;
                margin-top: 20px;
                line-height: 1.4;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🤖</div>
                <h1>Trading Bot System</h1>
                <p>Phân tích PnL & Khối lượng</p>
            </div>
            
            <div id="loginSection" class="login-form">
                <h2 style="color: white; margin-bottom: 25px; text-align: center;">🔐 Kết nối Binance</h2>
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="text" class="form-control" id="apiKey" placeholder="Nhập Binance API Key của bạn">
                </div>
                <div class="form-group">
                    <label>API Secret:</label>
                    <input type="password" class="form-control" id="apiSecret" placeholder="Nhập Binance API Secret của bạn">
                </div>
                <button class="btn" onclick="connectBinance()">
                    <span id="btnText">🔗 Kết nối Binance</span>
                    <span id="btnLoading" class="hidden">🔄 Đang kết nối...</span>
                </button>
                <div id="loginMessage"></div>
                
                <div class="info-text">
                    🔒 Thông tin API của bạn chỉ được lưu trữ tạm thời trên máy chủ và sẽ bị xóa khi bạn đóng trình duyệt.
                </div>
            </div>

            <div id="mainApp" class="hidden">
                <!-- Main app content sẽ được tải bằng JavaScript -->
            </div>
        </div>

        <script>
            async function connectBinance() {
                const apiKey = document.getElementById('apiKey').value.trim();
                const apiSecret = document.getElementById('apiSecret').value.trim();
                const messageDiv = document.getElementById('loginMessage');
                const btnText = document.getElementById('btnText');
                const btnLoading = document.getElementById('btnLoading');

                if (!apiKey || !apiSecret) {
                    showMessage('⚠️ Vui lòng nhập đầy đủ API Key và Secret', 'error');
                    return;
                }

                // Hiển thị trạng thái loading
                btnText.classList.add('hidden');
                btnLoading.classList.remove('hidden');
                showMessage('🔄 Đang kết nối đến Binance...', 'loading');

                try {
                    const response = await fetch('/api/connect', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            api_key: apiKey, 
                            api_secret: apiSecret 
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        showMessage('✅ ' + result.message, 'success');
                        setTimeout(() => {
                            document.getElementById('loginSection').classList.add('hidden');
                            document.getElementById('mainApp').classList.remove('hidden');
                            loadMainApp();
                        }, 1500);
                    } else {
                        showMessage('❌ ' + result.message, 'error');
                    }
                } catch (error) {
                    showMessage('❌ Lỗi kết nối: ' + error.message, 'error');
                } finally {
                    // Ẩn trạng thái loading
                    btnText.classList.remove('hidden');
                    btnLoading.classList.add('hidden');
                }
            }

            function showMessage(message, type) {
                const messageDiv = document.getElementById('loginMessage');
                messageDiv.innerHTML = message;
                messageDiv.className = 'message ' + type;
            }

            function loadMainApp() {
                // Tải giao diện chính từ file HTML riêng
                fetch('/app')
                    .then(response => response.text())
                    .then(html => {
                        document.getElementById('mainApp').innerHTML = html;
                        initializeApp();
                    })
                    .catch(error => {
                        console.error('Lỗi tải app:', error);
                        document.getElementById('mainApp').innerHTML = '<div style="color: white; text-align: center; padding: 40px;">❌ Lỗi tải ứng dụng. Vui lòng thử lại.</div>';
                    });
            }

            // Đăng ký Service Worker cho PWA
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                    navigator.serviceWorker.register('/static/sw.js')
                        .then(function(registration) {
                            console.log('ServiceWorker đăng ký thành công: ', registration.scope);
                        })
                        .catch(function(error) {
                            console.log('ServiceWorker đăng ký thất bại: ', error);
                        });
                });
            }

            // Cho phép submit form bằng phím Enter
            document.addEventListener('DOMContentLoaded', function() {
                const apiKeyInput = document.getElementById('apiKey');
                const apiSecretInput = document.getElementById('apiSecret');
                
                function handleEnterKey(event) {
                    if (event.key === 'Enter') {
                        connectBinance();
                    }
                }
                
                if (apiKeyInput) apiKeyInput.addEventListener('keypress', handleEnterKey);
                if (apiSecretInput) apiSecretInput.addEventListener('keypress', handleEnterKey);
            });
        </script>
    </body>
    </html>
    """

@app.get("/app", response_class=HTMLResponse)
async def get_app():
    """Trả về giao diện ứng dụng chính"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/manifest.json")
async def get_manifest():
    """Trả về manifest.json cho PWA"""
    return FileResponse("static/manifest.json")

@app.get("/sw.js")
async def get_sw():
    """Trả về service worker"""
    return FileResponse("static/sw.js", media_type="application/javascript")

@app.post("/api/connect")
async def connect_binance(credentials: UserCredentials):
    """Kết nối với Binance API"""
    try:
        # Test connection
        from binance_client import get_balance
        balance = get_balance(credentials.api_key, credentials.api_secret)
        
        if balance is None:
            return JSONResponse({
                "success": False, 
                "message": "Không thể kết nối Binance. Kiểm tra API Key/Secret và kết nối mạng."
            })
        
        # Create or update bot manager for this session
        user_id = "user_001"  # In a real app, you'd use session/user ID
        user_bot_managers[user_id] = BotManager(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Kết nối thành công! Số dư: {balance:.2f} USDC",
            "balance": balance
        })
        
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Lỗi kết nối: {str(e)}"
        })

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket
    
    try:
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            # Process any incoming messages if needed
    except WebSocketDisconnect:
        if user_id in active_connections:
            del active_connections[user_id]

@app.get("/api/system-info")
async def get_system_info():
    """Lấy thông tin hệ thống"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    bot_manager = user_bot_managers[user_id]
    info = bot_manager.get_system_info()
    return JSONResponse(info)

@app.get("/api/bots")
async def get_bots():
    """Lấy danh sách bot"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    bot_manager = user_bot_managers[user_id]
    bots_info = bot_manager.get_bots_info()
    return JSONResponse(bots_info)

@app.post("/api/add-bot")
async def add_bot(config: BotConfig):
    """Thêm bot mới"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    bot_manager = user_bot_managers[user_id]
    
    success = bot_manager.add_bot(
        symbol=config.symbol,
        lev=config.lev,
        percent=config.percent,
        tp=config.tp,
        sl=config.sl,
        roi_trigger=config.roi_trigger,
        strategy_type="Global-Market-PnL-Khối-Lượng",
        bot_mode=config.bot_mode,
        bot_count=config.bot_count
    )
    
    return JSONResponse({
        "success": success,
        "message": "Thêm bot thành công" if success else "Thêm bot thất bại"
    })

@app.post("/api/stop-bot")
async def stop_bot(request: StopBotRequest):
    """Dừng bot"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    bot_manager = user_bot_managers[user_id]
    
    if request.bot_id == "all":
        bot_manager.stop_all()
        return JSONResponse({"success": True, "message": "Đã dừng tất cả bot"})
    
    success = bot_manager.stop_bot(request.bot_id)
    return JSONResponse({
        "success": success,
        "message": "Dừng bot thành công" if success else "Không tìm thấy bot"
    })

@app.get("/api/balance")
async def get_balance():
    """Lấy số dư"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    from binance_client import get_balance
    bot_manager = user_bot_managers[user_id]
    balance = get_balance(bot_manager.api_key, bot_manager.api_secret)
    return JSONResponse({"balance": balance})

@app.get("/api/positions")
async def get_positions():
    """Lấy vị thế hiện tại"""
    user_id = "user_001"
    if user_id not in user_bot_managers:
        raise HTTPException(status_code=400, detail="Chưa kết nối Binance")
    
    from binance_client import get_positions
    bot_manager = user_bot_managers[user_id]
    positions = get_positions(api_key=bot_manager.api_key, api_secret=bot_manager.api_secret)
    
    active_positions = []
    for pos in positions:
        position_amt = float(pos.get('positionAmt', 0))
        if position_amt != 0:
            active_positions.append({
                'symbol': pos.get('symbol'),
                'side': 'LONG' if position_amt > 0 else 'SHORT',
                'positionAmt': abs(position_amt),
                'entryPrice': float(pos.get('entryPrice', 0)),
                'unRealizedProfit': float(pos.get('unRealizedProfit', 0)),
                'leverage': float(pos.get('leverage', 1))
            })
    
    return JSONResponse(active_positions)

# Background task để gửi updates định kỳ
async def background_updates():
    while True:
        try:
            for user_id, websocket in list(active_connections.items()):
                if user_id in user_bot_managers:
                    bot_manager = user_bot_managers[user_id]
                    system_info = bot_manager.get_system_info()
                    bots_info = bot_manager.get_bots_info()
                    
                    try:
                        await websocket.send_json({
                            "type": "update",
                            "system_info": system_info,
                            "bots_info": bots_info
                        })
                    except:
                        # Remove disconnected clients
                        if user_id in active_connections:
                            del active_connections[user_id]
        
        except Exception as e:
            logger.error(f"Background update error: {str(e)}")
        
        await asyncio.sleep(3)  # Update mỗi 3 giây

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_updates())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
