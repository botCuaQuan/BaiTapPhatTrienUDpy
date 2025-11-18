// app.js

// 🔧 SỬA DÒNG NÀY: để URL backend trên Railway
// Ví dụ: const API_BASE = "https://ten-backend-cua-ban.up.railway.app";
const API_BASE = ""; // nếu serve chung domain với backend thì để trống

// Helper gọi API JSON
async function apiRequest(path, options = {}) {
    const url = API_BASE + path;
    const defaultHeaders = {
        "Content-Type": "application/json",
    };
    const opts = {
        headers: defaultHeaders,
        ...options,
    };
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
}

const appEl = document.getElementById("app");

// Render màn hình cấu hình tài khoản (chưa nhập API)
function renderSetupAccount(statusMsg = "") {
    appEl.innerHTML = `
        <h1>⚙️ Cấu hình tài khoản Binance Futures</h1>
        <div class="card">
            <h2>🔑 Nhập API Key & Secret</h2>
            ${statusMsg ? `<div class="status err">${statusMsg}</div>` : ""}
            <form id="setup-form">
                <label>API Key</label>
                <input type="password" name="api_key" required />

                <label>API Secret</label>
                <input type="password" name="api_secret" required />

                <br />
                <button class="btn btn-primary" type="submit">Lưu & Khởi tạo Bot Manager</button>
            </form>
            <p><small>Lưu ý: API/Secret chỉ lưu trên server (RAM), không ghi ra file từ frontend.</small></p>
        </div>
    `;

    const form = document.getElementById("setup-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const api_key = formData.get("api_key");
        const api_secret = formData.get("api_secret");

        form.querySelector("button").disabled = true;

        try {
            await apiRequest("/api/setup-account", {
                method: "POST",
                body: JSON.stringify({ api_key, api_secret }),
            });
            // Sau khi setup xong, load dashboard
            await renderDashboard();
        } catch (err) {
            console.error(err);
            renderSetupAccount("Không lưu được API/Secret: " + err.message);
        }
    });
}

// Render màn hình dashboard (đã cấu hình tài khoản)
async function renderDashboard(statusMsg = "") {
    if (!statusMsg) statusMsg = "";

    // Lấy summary & danh sách bot
    let summary = "";
    let bots = [];

    try {
        const s = await apiRequest("/api/summary");
        summary = s.summary || "";
    } catch (err) {
        summary = "Lỗi lấy summary: " + err.message;
    }

    try {
        const b = await apiRequest("/api/bots");
        bots = b.bots || [];
    } catch (err) {
        bots = [];
        statusMsg = "Lỗi lấy danh sách bot: " + err.message;
    }

    const botCards = bots
        .map((b) => {
            return `
            <div class="card">
                <h3>🤖 ${b.bot_id}</h3>
                <p>
                    <span class="badge">Mode: ${b.mode}</span>
                    &nbsp;&nbsp;
                    Coin đang theo dõi: <b>${b.active_coins}</b> / ${b.max_coins}
                </p>
                <button class="btn btn-danger" data-action="stop-bot" data-bot-id="${b.bot_id}">
                    ⛔ Dừng bot này
                </button>
            </div>
        `;
        })
        .join("");

    const botsSection = botCards || "<p><small>Hiện chưa có bot nào đang chạy.</small></p>";

    appEl.innerHTML = `
        <h1>🤖 Trading Bot – Web UI (Frontend)</h1>
        <p>API Key/Secret đã được cấu hình trên backend. Bạn điều khiển bot trực tiếp tại đây.</p>

        <div class="card">
            <h2>📊 Thống kê nhanh</h2>
            ${
                statusMsg
                    ? `<div class="status ${statusMsg.startsWith("Lỗi") ? "err" : "ok"}">${statusMsg}</div>`
                    : ""
            }
            <pre>${summary}</pre>
            <button class="btn btn-secondary" id="refresh-summary">🔄 Refresh summary</button>
        </div>

        <div class="card">
            <h2>➕ Tạo bot mới</h2>
            <form id="add-bot-form">
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
                        <input type="text" name="symbol" placeholder="XRPUSDC (để trống nếu Dynamic)" />
                    </div>
                </div>

                <div class="row">
                    <div>
                        <label>Đòn bẩy (leverage)</label>
                        <input type="number" name="lev" value="10" min="1" max="125" required />
                    </div>
                    <div>
                        <label>% số dư cho mỗi lệnh</label>
                        <input type="number" name="percent" value="5" min="1" max="100" step="0.1" required />
                    </div>
                </div>

                <div class="row">
                    <div>
                        <label>TP %</label>
                        <input type="number" name="tp" value="50" min="1" step="1" required />
                    </div>
                    <div>
                        <label>SL % (0 = tắt SL cố định)</label>
                        <input type="number" name="sl" value="0" min="0" step="1" required />
                    </div>
                </div>

                <div class="row">
                    <div>
                        <label>ROI trigger % (0 = tắt)</label>
                        <input type="number" name="roi_trigger" value="0" min="0" step="1" />
                    </div>
                    <div>
                        <label>Số coin tối đa bot quản lý</label>
                        <input type="number" name="bot_count" value="3" min="1" max="20" required />
                    </div>
                </div>

                <br />
                <button class="btn btn-primary" type="submit">🚀 Tạo bot</button>
            </form>
        </div>

        <div class="card">
            <h2>📋 Danh sách bot</h2>
            <div id="bots-list">
                ${botsSection}
            </div>
            <hr />
            <button class="btn btn-danger" id="stop-all-bots">🛑 Dừng TẤT CẢ bot</button>
            &nbsp;
            <button class="btn btn-secondary" id="stop-all-coins">⛔ Dừng toàn bộ COIN</button>
        </div>
    `;

    // Event: refresh summary
    document.getElementById("refresh-summary").addEventListener("click", async () => {
        await renderDashboard();
    });

    // Event: add bot
    document.getElementById("add-bot-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);

        const payload = {
            bot_mode: formData.get("bot_mode"),
            symbol: formData.get("symbol") || "",
            lev: Number(formData.get("lev")),
            percent: Number(formData.get("percent")),
            tp: Number(formData.get("tp")),
            sl: Number(formData.get("sl")),
            roi_trigger: Number(formData.get("roi_trigger") || 0),
            bot_count: Number(formData.get("bot_count")),
        };

        form.querySelector("button").disabled = true;

        try {
            const res = await apiRequest("/api/add-bot", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                throw new Error("API trả về ok=false");
            }
            await renderDashboard("Tạo bot thành công.");
        } catch (err) {
            console.error(err);
            await renderDashboard("Lỗi tạo bot: " + err.message);
        }
    });

    // Event: stop all bots
    document.getElementById("stop-all-bots").addEventListener("click", async () => {
        try {
            await apiRequest("/api/stop-all-bots", { method: "POST" });
            await renderDashboard("Đã dừng tất cả bot.");
        } catch (err) {
            await renderDashboard("Lỗi dừng tất cả bot: " + err.message);
        }
    });

    // Event: stop all coins
    document.getElementById("stop-all-coins").addEventListener("click", async () => {
        try {
            await apiRequest("/api/stop-all-coins", { method: "POST" });
            await renderDashboard("Đã dừng toàn bộ coin.");
        } catch (err) {
            await renderDashboard("Lỗi dừng toàn bộ coin: " + err.message);
        }
    });

    // Event: stop 1 bot (delegate)
    document.getElementById("bots-list").addEventListener("click", async (e) => {
        const btn = e.target.closest("button[data-action='stop-bot']");
        if (!btn) return;
        const botId = btn.getAttribute("data-bot-id");
        if (!botId) return;

        btn.disabled = true;
        try {
            await apiRequest("/api/stop-bot", {
                method: "POST",
                body: JSON.stringify({ bot_id: botId }),
            });
            await renderDashboard(`Đã dừng bot: ${botId}`);
        } catch (err) {
            await renderDashboard("Lỗi dừng bot: " + err.message);
        }
    });
}

// Khởi động app: kiểm tra đã cấu hình tài khoản chưa
async function init() {
    try {
        const status = await apiRequest("/api/account-status");
        if (status.configured) {
            await renderDashboard();
        } else {
            renderSetupAccount();
        }
    } catch (err) {
        console.error(err);
        appEl.innerHTML = `
            <h1>Lỗi kết nối backend</h1>
            <p>Không gọi được API backend: ${err.message}</p>
            <p>Kiểm tra xem backend FastAPI (PHẦN 1) đã chạy trên Railway chưa nhé.</p>
        `;
    }
}

init();
