from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import json
import asyncio
import threading
import time
from typing import Dict, Optional, List
import logging

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

# Pydantic models for request/response
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading Bot System</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px; 
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { 
                background: rgba(255, 255, 255, 0.1); 
                backdrop-filter: blur(10px); border-radius: 15px; 
                padding: 20px; margin-bottom: 20px; 
                border: 1px solid rgba(255, 255, 255, 0.2); 
            }
            .header h1 { color: white; text-align: center; margin-bottom: 10px; }
            .login-form {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px); border-radius: 15px;
                padding: 20px; margin-bottom: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; color: white; margin-bottom: 5px; }
            .form-control { 
                width: 100%; padding: 10px; border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.1); color: white;
            }
            .btn { 
                background: #667eea; color: white; border: none;
                padding: 12px 20px; border-radius: 5px; cursor: pointer;
                width: 100%; margin-top: 10px;
            }
            .btn:hover { background: #764ba2; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Trading Bot System - Phân Tích PnL & Khối Lượng</h1>
            </div>
            
            <div id="loginSection" class="login-form">
                <h2 style="color: white; margin-bottom: 20px;">🔐 Kết nối Binance</h2>
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="text" class="form-control" id="apiKey" placeholder="Nhập Binance API Key">
                </div>
                <div class="form-group">
                    <label>API Secret:</label>
                    <input type="password" class="form-control" id="apiSecret" placeholder="Nhập Binance API Secret">
                </div>
                <button class="btn" onclick="connectBinance()">🔗 Kết nối</button>
                <div id="loginMessage" style="color: white; margin-top: 10px; text-align: center;"></div>
            </div>

            <div id="mainApp" class="hidden">
                <!-- Main app content will be loaded by JavaScript -->
            </div>
        </div>

        <script>
            async function connectBinance() {
                const apiKey = document.getElementById('apiKey').value;
                const apiSecret = document.getElementById('apiSecret').value;
                const messageDiv = document.getElementById('loginMessage');

                if (!apiKey || !apiSecret) {
                    messageDiv.innerHTML = '⚠️ Vui lòng nhập đầy đủ API Key và Secret';
                    return;
                }

                messageDiv.innerHTML = '🔄 Đang kết nối...';

                try {
                    const response = await fetch('/api/connect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret })
                    });

                    const result = await response.json();

                    if (result.success) {
                        messageDiv.innerHTML = '✅ Kết nối thành công!';
                        document.getElementById('loginSection').classList.add('hidden');
                        document.getElementById('mainApp').classList.remove('hidden');
                        loadMainApp();
                    } else {
                        messageDiv.innerHTML = '❌ ' + result.message;
                    }
                } catch (error) {
                    messageDiv.innerHTML = '❌ Lỗi kết nối: ' + error.message;
                }
            }

            function loadMainApp() {
                // Load the main application interface
                fetch('/static/index.html')
                    .then(response => response.text())
                    .then(html => {
                        document.getElementById('mainApp').innerHTML = html;
                        initializeApp();
                    });
            }

            function initializeApp() {
                // This function will be implemented in the main app JavaScript
                console.log('Main app initialized');
            }
        </script>
    </body>
    </html>
    """

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
            # Keep connection alive
            await asyncio.sleep(10)
            if user_id in user_bot_managers:
                bot_manager = user_bot_managers[user_id]
                system_info = bot_manager.get_system_info()
                bots_info = bot_manager.get_bots_info()
                
                await websocket.send_json({
                    "type": "update",
                    "system_info": system_info,
                    "bots_info": bots_info
                })
                
    except WebSocketDisconnect:
        if user_id in active_connections:
            del active_connections[user_id]

@app.get("/api/system-info")
async def get_system_info():
    """Lấy thông tin hệ thống"""
    user_id = "user_001"  # In real app, get from session
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
        
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_updates())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
