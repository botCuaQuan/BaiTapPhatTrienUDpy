// app.js

// 🔧 Nếu backend deploy riêng domain thì set API_BASE = "https://..."
// còn hiện tại backend + frontend chung trên Railway / local thì để rỗng
const API_BASE = "";

// Token & user toàn cục
let authToken = null;
let currentUsername = null;

// Chart & WebSocket
let priceChart = null;
let priceData = [];
let labelData = [];
let ws = null;

// =============== Helper API ===============

async function apiRequest(path, { method = "GET", body = null, auth = true } = {}) {
    const url = API_BASE + path;
    const headers = {
        "Content-Type": "application/json",
    };
    if (auth && authToken) {
        headers["X-Auth-Token"] = authToken;
    }

    const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null,
    });

    if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || `HTTP ${res.status}`);
    }

    return res.json();
}

// =============== Render chung ===============

function renderBaseLayout(inner) {
    const app = document.getElementById("app");
    app.innerHTML = `
        <div class="topbar">
            <div class="topbar-left">
                <div class="logo-circle">Q</div>
                <div>
                    <div class="topbar-title">QUAN TERMINAL</div>
                    <div class="topbar-sub">Multi-exchange Trading Bot Dashboard</div>
                </div>
            </div>
            <div class="topbar-right">
                <div class="badge">
                    <div class="badge-dot"></div>
                    <span id="ws-status-text">WS: Đang kết nối...</span>
                </div>
                <div class="user-chip">
                    <div class="user-avatar">${(currentUsername || "U")[0].toUpperCase()}</div>
                    <div>
                        <div>${currentUsername || "Guest"}</div>
                        <div style="font-size:11px; color:#9ca3af;">Paper / Demo mode</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="shell">
            <aside class="sidebar">
                <div style="flex:1;">
                    <div class="sidebar-section-title">Main</div>
                    <div class="nav-item nav-item-active">
                        <span><span class="nav-dot"></span><span>Overview</span></span>
                        <span style="font-size:11px;">⌘1</span>
                    </div>
                    <div class="nav-item">
                        <span><span class="nav-dot"></span><span>Bots</span></span>
                        <span style="font-size:11px;">⌘2</span>
                    </div>
                </div>
                <div class="sidebar-footer">
                    <div>Backend: <b>FastAPI</b></div>
                    <div>Realtime: <b>WebSocket</b></div>
                </div>
            </aside>
            <main class="content">
                ${inner}
            </main>
        </div>
    `;
}

// =============== AUTH ===============

function renderAuthScreen(message = "") {
    const app = document.getElementById("app");
    app.innerHTML = `
        <div class="topbar">
            <div class="topbar-left">
                <div class="logo-circle">Q</div>
                <div>
                    <div class="topbar-title">QUAN TERMINAL</div>
                    <div class="topbar-sub">Đăng nhập để điều khiển bot</div>
                </div>
            </div>
        </div>
        <div class="auth-wrapper">
            <div class="auth-card">
                <h2>Đăng nhập</h2>
                <p>Tài khoản được lưu trên DB, có thể dùng lại trên môi trường khác.</p>
                ${message ? `<div class="status err">${message}</div>` : ""}
                <form id="auth-form">
                    <div class="form-group">
                        <label>Username</label>
                        <input name="username" type="text" required />
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input name="password" type="password" required />
                    </div>
                    <div class="btn-row">
                        <button class="btn btn-primary" type="submit" data-action="login">Đăng nhập</button>
                        <button class="btn btn-secondary" type="button" id="btn-register">Đăng ký & đăng nhập</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    const form = document.getElementById("auth-form");
    const btnRegister = document.getElementById("btn-register");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const username = fd.get("username").trim();
        const password = fd.get("password");

        if (!username || !password) {
            renderAuthScreen("Không được để trống username/password.");
            return;
        }

        try {
            const data = await apiRequest("/api/login", {
                method: "POST",
                body: { username, password },
                auth: false,
            });
            authToken = data.token;
            currentUsername = data.username;
            localStorage.setItem("authToken", authToken);
            localStorage.setItem("username", currentUsername);
            await afterLogin();
        } catch (err) {
            renderAuthScreen("Lỗi đăng nhập: " + err.message);
        }
    });

    btnRegister.addEventListener("click", async () => {
        const fd = new FormData(form);
        const username = fd.get("username").trim();
        const password = fd.get("password");
        if (!username || !password) {
            renderAuthScreen("Không được để trống username/password.");
            return;
        }
        try {
            const data = await apiRequest("/api/register", {
                method: "POST",
                body: { username, password },
                auth: false,
            });
            authToken = data.token;
            currentUsername = data.username;
            localStorage.setItem("authToken", authToken);
            localStorage.setItem("username", currentUsername);
            await afterLogin();
        } catch (err) {
            renderAuthScreen("Lỗi đăng ký: " + err.message);
        }
    });
}

// =============== SETUP API KEY ===============

function renderSetupAccount(message = "") {
    renderBaseLayout(`
        <div class="setup-wrapper">
            <div class="setup-card">
                <h2>Cấu hình API Binance</h2>
                <p>Nhập API Key & Secret. Cấu hình này được lưu trong DB theo user.</p>
                ${message ? `<div class="status err">${message}</div>` : ""}
                <form id="setup-form">
                    <div class="form-group">
                        <label>API Key</label>
                        <input name="api_key" type="text" required />
                    </div>
                    <div class="form-group">
                        <label>API Secret</label>
                        <input name="api_secret" type="password" required />
                    </div>
                    <div class="btn-row">
                        <button class="btn btn-primary" type="submit">Lưu cấu hình & vào Dashboard</button>
                        <button class="btn btn-secondary" type="button" id="btn-logout">Đăng xuất</button>
                    </div>
                </form>
            </div>
        </div>
    `);

    document.getElementById("btn-logout").addEventListener("click", () => {
        authToken = null;
        currentUsername = null;
        localStorage.removeItem("authToken");
        localStorage.removeItem("username");
        if (ws) ws.close();
        renderAuthScreen();
    });

    document.getElementById("setup-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const api_key = fd.get("api_key").trim();
        const api_secret = fd.get("api_secret").trim();

        if (!api_key || !api_secret) {
            renderSetupAccount("Không được để trống API key/secret.");
            return;
        }

        try {
            await apiRequest("/api/setup-account", {
                method: "POST",
                body: { api_key, api_secret },
            });
            await renderDashboard("Cấu hình API thành công.");
        } catch (err) {
            renderSetupAccount("Lỗi lưu cấu hình: " + err.message);
        }
    });
}

// =============== DASHBOARD ===============

function initChart() {
    const ctx = document.getElementById("priceChart").getContext("2d");
    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labelData,
            datasets: [
                {
                    label: "Price",
                    data: priceData,
                    borderWidth: 1.8,
                    tension: 0.3,
                    pointRadius: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: { color: "#9ca3af", maxTicksLimit: 6 },
                    grid: { display: false },
                },
                y: {
                    ticks: { color: "#9ca3af", maxTicksLimit: 5 },
                    grid: { color: "rgba(31,41,55,0.7)" },
                },
            },
        },
    });
}

function connectPriceWS() {
    if (ws) {
        ws.close();
    }
    const statusEl = document.getElementById("ws-status-text");
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${scheme}://${window.location.host}/ws/prices`;

    ws = new WebSocket(url);

    ws.onopen = () => {
        if (statusEl) statusEl.textContent = "WS: Connected";
    };
    ws.onclose = () => {
        if (statusEl) statusEl.textContent = "WS: Disconnected - reconnecting...";
        setTimeout(connectPriceWS, 2000);
    };
    ws.onerror = () => {
        if (statusEl) statusEl.textContent = "WS: Error";
    };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const { symbol, price, change, volume, timestamp } = data;

        const timeStr = new Date(timestamp * 1000).toLocaleTimeString("vi-VN", {
            hour12: false,
        });

        // Update metrics
        const metricPrice = document.getElementById("metric-price");
        const metricChange = document.getElementById("metric-change");
        const metricVolume = document.getElementById("metric-volume");
        const symbolText = document.getElementById("symbol-text");

        if (metricPrice) metricPrice.textContent = price.toFixed(2);
        if (metricVolume) metricVolume.textContent = volume.toFixed(2);
        if (symbolText) symbolText.textContent = symbol;

        if (metricChange) {
            metricChange.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}`;
            metricChange.classList.remove("metric-up", "metric-down");
            metricChange.classList.add(change >= 0 ? "metric-up" : "metric-down");
        }

        // Chart
        priceData.push(price);
        labelData.push(timeStr);
        if (priceData.length > 60) {
            priceData.shift();
            labelData.shift();
        }
        if (priceChart) {
            priceChart.data.labels = labelData;
            priceChart.data.datasets[0].data = priceData;
            priceChart.update("none");
        }

        // Bảng ticks
        const tbody = document.getElementById("ticks-body");
        if (tbody) {
            const tr = document.createElement("tr");
            const side = change >= 0 ? "BUY" : "SELL";
            tr.innerHTML = `
                <td>${timeStr}</td>
                <td>${symbol}</td>
                <td>${price.toFixed(2)}</td>
                <td style="color:${change >= 0 ? "#22c55e" : "#ef4444"};">
                    ${change >= 0 ? "+" : ""}${change.toFixed(2)}
                </td>
                <td>${volume.toFixed(2)}</td>
                <td>
                    <span class="chip-mini ${side === "BUY" ? "chip-buy" : "chip-sell"}">${side}</span>
                </td>
            `;
            tbody.prepend(tr);
            while (tbody.rows.length > 20) {
                tbody.deleteRow(tbody.rows.length - 1);
            }
        }
    };
}

async function renderDashboard(statusMsg = "") {
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
        statusMsg = statusMsg || ("Lỗi lấy danh sách bot: " + err.message);
    }

    const botCards = bots
        .map(
            (b) => `
        <div class="card" style="margin-top:8px;">
            <div class="card-header">
                <div class="card-title">🤖 Bot ${b.bot_id}</div>
                <button class="btn btn-secondary btn-stop-one" data-id="${b.bot_id}">Dừng bot</button>
            </div>
            <div style="font-size:12px; margin-top:6px;">
                <span class="chip-mini">Mode: ${b.mode}</span>
                &nbsp;&nbsp;
                Coin đang theo dõi: <b>${b.active_coins}</b> / ${b.max_coins}
            </div>
        </div>
    `
        )
        .join("");

    renderBaseLayout(`
        <div class="content-header">
            <div>
                <div class="content-title">
                    Live Market
                    <span class="symbol-badge">
                        <span id="symbol-text">BTCUSDT</span>
                    </span>
                </div>
                <div class="content-subtitle">
                    Biểu đồ + bảng realtime (WebSocket) + summary bot (REST).
                </div>
            </div>
            <div class="btn-row">
                <button class="btn btn-secondary" id="refresh-summary">Refresh summary</button>
                <button class="btn btn-secondary" id="btn-logout">Đăng xuất</button>
            </div>
        </div>

        <div class="grid-main">
            <!-- LEFT: Price chart + summary -->
            <section class="card">
                <div class="card-header">
                    <div class="card-title">Price Action</div>
                    <div style="font-size:11px; color:#9ca3af;">
                        Last update: realtime từ WS
                    </div>
                </div>

                <div class="metric-row">
                    <div class="metric-pill">
                        <div class="metric-label">Last Price</div>
                        <div class="metric-value" id="metric-price">-</div>
                    </div>
                    <div class="metric-pill">
                        <div class="metric-label">24h Δ (fake demo)</div>
                        <div class="metric-value" id="metric-change">-</div>
                    </div>
                    <div class="metric-pill">
                        <div class="metric-label">Volume</div>
                        <div class="metric-value" id="metric-volume">-</div>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="priceChart"></canvas>
                </div>

                <div class="summary-box">
                    <b>Summary vị thế & bot:</b>
                    <br />
                    ${summary.replace(/\n/g, "<br />")}
                </div>
            </section>

            <!-- RIGHT: create bot + list bot -->
            <section class="card">
                <div class="card-header">
                    <div class="card-title">Quản lý bot</div>
                    <div style="font-size:11px; color:#9ca3af;">
                        Cấu hình sẽ được lưu vào DB (BotConfig).
                    </div>
                </div>

                ${
                    statusMsg
                        ? `<div class="status ${statusMsg.startsWith("Lỗi") ? "err" : "ok"}" style="margin-top:6px;">${statusMsg}</div>`
                        : ""
                }

                <h3 style="font-size:13px; margin-top:8px;">Tạo bot mới</h3>

                <form id="add-bot-form">
                    <div class="form-grid">
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

                        <div>
                            <label>Đòn bẩy (lev)</label>
                            <input type="number" name="lev" value="10" min="1" max="125" required />
                        </div>
                        <div>
                            <label>% số dư cho mỗi lệnh</label>
                            <input type="number" name="percent" value="5" min="1" max="100" step="0.1" required />
                        </div>

                        <div>
                            <label>TP %</label>
                            <input type="number" name="tp" value="50" min="1" step="1" required />
                        </div>
                            <label>SL % (0 = tắt SL cố định)</label>
                            <input type="number" name="sl" value="0" min="0" step="1" required />
                        <div>
                        </div>

                        <div>
                            <label>ROI trigger % (0 = bỏ qua)</label>
                            <input type="number" name="roi_trigger" value="0" min="0" step="1" />
                        </div>
                        <div>
                            <label>Số lượng bot song song</label>
                            <input type="number" name="bot_count" value="1" min="1" max="10" />
                        </div>
                    </div>

                    <div class="btn-row">
                        <button class="btn btn-primary" type="submit">Thêm bot & lưu cấu hình</button>
                        <button class="btn btn-danger" type="button" id="stop-all-bots">Dừng TẤT CẢ bot</button>
                        <button class="btn btn-secondary" type="button" id="stop-all-coins">Dừng toàn bộ COIN</button>
                    </div>
                </form>

                ${botCards || `<div style="font-size:12px; margin-top:8px; color:#9ca3af;">Chưa có bot nào.</div>`}
            </section>
        </div>

        <!-- Bảng ticks realtime -->
        <section class="card" style="margin-top:10px;">
            <div class="card-header">
                <div class="card-title">Realtime ticks (WebSocket /ws/prices)</div>
                <div style="font-size:11px; color:#9ca3af;">Giữ tối đa 20 dòng gần nhất.</div>
            </div>
            <div style="margin-top:6px;">
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Price</th>
                            <th>Change</th>
                            <th>Vol</th>
                            <th>Side</th>
                        </tr>
                    </thead>
                    <tbody id="ticks-body"></tbody>
                </table>
            </div>
        </section>
    `;

    // Gắn event
    document.getElementById("btn-logout").addEventListener("click", () => {
        authToken = null;
        currentUsername = null;
        localStorage.removeItem("authToken");
        localStorage.removeItem("username");
        if (ws) ws.close();
        renderAuthScreen();
    });

    document.getElementById("refresh-summary").addEventListener("click", async () => {
        await renderDashboard();
    });

    document.getElementById("stop-all-bots").addEventListener("click", async () => {
        try {
            await apiRequest("/api/stop-all-bots", { method: "POST" });
            await renderDashboard("Đã dừng tất cả bot.");
        } catch (err) {
            await renderDashboard("Lỗi dừng tất cả bot: " + err.message);
        }
    });

    document.getElementById("stop-all-coins").addEventListener("click", async () => {
        try {
            await apiRequest("/api/stop-all-coins", { method: "POST" });
            await renderDashboard("Đã dừng toàn bộ coin.");
        } catch (err) {
            await renderDashboard("Lỗi dừng toàn bộ coin: " + err.message);
        }
    });

    document.querySelectorAll(".btn-stop-one").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.getAttribute("data-id");
            try {
                await apiRequest("/api/stop-bot", {
                    method: "POST",
                    body: { bot_id: id },
                });
                await renderDashboard(`Đã dừng bot ${id}.`);
            } catch (err) {
                await renderDashboard("Lỗi dừng bot: " + err.message);
            }
        });
    });

    document.getElementById("add-bot-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const payload = {
            bot_mode: fd.get("bot_mode"),
            symbol: fd.get("symbol") || "",
            lev: Number(fd.get("lev")),
            percent: Number(fd.get("percent")),
            tp: Number(fd.get("tp")),
            sl: Number(fd.get("sl")),
            roi_trigger: Number(fd.get("roi_trigger")),
            bot_count: Number(fd.get("bot_count")),
        };

        try {
            const res = await apiRequest("/api/add-bot", {
                method: "POST",
                body: payload,
            });
            if (!res.ok) throw new Error("Add bot trả về ok=false");
            await renderDashboard("Thêm bot thành công & đã lưu cấu hình.");
        } catch (err) {
            await renderDashboard("Lỗi thêm bot: " + err.message);
        }
    });

    // Khởi tạo chart + WebSocket realtime
    priceData = [];
    labelData = [];
    initChart();
    connectPriceWS();
}

// =============== After login & init ===============

async function afterLogin() {
    try {
        const status = await apiRequest("/api/account-status");
        if (status.configured) {
            await renderDashboard();
        } else {
            renderSetupAccount();
        }
    } catch (err) {
        authToken = null;
        currentUsername = null;
        localStorage.removeItem("authToken");
        localStorage.removeItem("username");
        renderAuthScreen("Phiên đăng nhập hết hạn, vui lòng đăng nhập lại.");
    }
}

function init() {
    authToken = localStorage.getItem("authToken");
    currentUsername = localStorage.getItem("username");
    if (authToken && currentUsername) {
        afterLogin();
    } else {
        renderAuthScreen();
    }
}

init();
