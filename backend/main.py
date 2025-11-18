from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sqlite3
from typing import Optional

# =========================
# Cấu hình DB người dùng
# =========================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(username: str, password: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # username đã tồn tại
        return False
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT password FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False
    return row["password"] == password


# =========================
# Khởi tạo FastAPI
# =========================

app = FastAPI(title="BaiTapPhatTrienUDpy API")

# CORS cho web & mobile (nếu cần)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # khi lên production thì siết lại
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# =========================
# Các API
# =========================

async def _get_username_password_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Hỗ trợ lấy username/password từ:
    - form HTML (application/x-www-form-urlencoded hoặc multipart/form-data)
    - hoặc body JSON
    """
    content_type = request.headers.get("content-type", "")

    username = None
    password = None

    if content_type.startswith("application/json"):
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

    return username, password


@app.post("/api/register")
async def api_register(request: Request):
    username, password = await _get_username_password_from_request(request)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password")

    ok = create_user(username, password)
    if not ok:
        # Username trùng
        raise HTTPException(status_code=400, detail="Username đã tồn tại")

    return {"success": True, "message": "Đăng ký thành công"}


@app.post("/api/login")
async def api_login(request: Request):
    username, password = await _get_username_password_from_request(request)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Thiếu username hoặc password")

    if not authenticate_user(username, password):
        raise HTTPException(status_code=401, detail="Sai username hoặc password")

    # Ở đây bạn có thể trả thêm token, hoặc thông tin cấu hình người dùng...
    return {"success": True, "message": "Đăng nhập thành công"}


@app.get("/api/ping")
async def ping():
    return {"status": "ok"}


# =========================
# Serve frontend
# =========================

FRONTEND_DIR = BASE_DIR / "frontend"

if not FRONTEND_DIR.exists():
    # Nếu quên tạo thư mục frontend thì ném lỗi rõ ràng
    raise RuntimeError(f"Thư mục frontend không tồn tại ở: {FRONTEND_DIR}")

# MOUNT CUỐI CÙNG, sau khi định nghĩa API
app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)


# =========================
# Chạy trực tiếp (local)
# =========================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
