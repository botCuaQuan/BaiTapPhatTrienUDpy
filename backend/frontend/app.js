// ====================== GLOBAL CONFIG ======================
const API_BASE = "";
let authToken = null;
let currentUsername = null;

// === DATA FOR WS ===
let currentSymbol = "BTCUSDT";  // mặc định
let priceChart = null;
let priceData = [];
let labelData = [];
let ws = null;


// ====================== API HELPER ======================
async function apiRequest(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && authToken) headers["X-Auth-Token"] = authToken;

  const resp = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  if (resp.status === 401) renderAuthScreen("Vui lòng đăng nhập lại!");
  if (!resp.ok) throw await resp.json();
  return await resp.json();
}


// ====================== AUTH UI ======================
function renderAuthScreen(msg = "") {
  const appEl = document.getElementById("app");
  appEl.innerHTML = `
    <div class="auth-box">
      <h2>🔐 Đăng nhập</h2>
      <input id="login-user" placeholder="Username" />
      <input id="login-pass" type="password" placeholder="Password" />
      <button id="btn-login">Đăng nhập</button>

      <h2>✍️ Đăng ký</h2>
      <input id="reg-user" placeholder="Username" />
      <input id="reg-pass" type="password" placeholder="Password" />
      <button id="btn-register">Đăng ký</button>

      <div class="error">${msg}</div>
    </div>
  `;

  document.getElementById("btn-login").onclick = async () => {
    const username = document.getElementById("login-user").value.trim();
    const password = document.getElementById("login-pass").value.trim();
    try {
      const data = await apiRequest("/api/login", { method: "POST", body: { username, password }, auth: false });
      authToken = data.token;
      currentUsername = data.username;
      renderDashboard();
    } catch (err) {
      renderAuthScreen(`Lỗi: ${err.detail || err}`);
    }
  };

  document.getElementById("btn-register").onclick = async () => {
    const username = document.getElementById("reg-user").value.trim();
    const password = document.getElementById("reg-pass").value.trim();
    try {
      const data = await apiRequest("/api/register", { method: "POST", body: { username, password }, auth: false });
      authToken = data.token;
      currentUsername = data.username;
      renderDashboard();
    } catch (err) {
      renderAuthScreen(`Lỗi: ${err.detail || err}`);
    }
  };
}


// ====================== DASHBOARD ======================
async function renderDashboard() {
  const appEl = document.getElementById("app");

  appEl.innerHTML = `
    <div class="topbar">
      <div>👤 ${currentUsername}</div>
      <button id="logout-btn" class="btn btn-secondary">Đăng xuất</button>
    </div>

    <div class="shell">
      <!-- CHỌN COIN -->
      <div class="card">
        <h3>Chọn Coin</h3>
        <input id="coin-input" placeholder="VD: ETHUSDT" />
        <button id="set-coin-btn" class="btn btn-primary">Set Coin</button>
      </div>

      <!-- METRICS -->
      <div class="metric-row">
        <div class="metric-pill"><div class="metric-label">Symbol</div><div class="metric-value" id="metric-symbol">${currentSymbol}</div></div>
        <div class="metric-pill"><div class="metric-label">Giá</div><div class="metric-value" id="metric-price">-</div></div>
        <div class="metric-pill"><div class="metric-label">Balance</div><div class="metric-value" id="metric-balance">-</div></div>
        <div class="metric-pill"><div class="metric-label">PnL</div><div class="metric-value" id="metric-pnl">-</div></div>
        <div class="metric-pill"><div class="metric-label">Bot chạy</div><div class="metric-value" id="metric-bot">-</div></div>
      </div>

      <!-- BIỂU ĐỒ -->
      <div class="card">
        <canvas id="priceChart" height="150"></canvas>
      </div>

      <!-- BẢNG DỮ LIỆU -->
      <div class="card">
        <h3>Lệnh Gần Nhất (fake)</h3>
        <table class="table-live">
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Price</th><th>Volume</th></tr>
          </thead>
          <tbody id="ticks-body"></tbody>
        </table>
      </div>

      <!-- API STATUS + BOTS -->
      <div class="card" id="status-box">Đang tải...</div>
      <div class="card" id="bots-box">Đang tải...</div>
    </div>
  `;


  // ========== EVENT SET COIN ==========
  document.getElementById("set-coin-btn").onclick = async () => {
    const coin = document.getElementById("coin-input").value.trim();
    if (!coin) return alert("Nhập coin!");
    try {
      await apiRequest("/api/set-symbol", { method: "POST", body: { symbol: coin }});
      currentSymbol = coin.toUpperCase();
      document.getElementById("metric-symbol").textContent = currentSymbol;
      reconnectWS();
    } catch {
      alert("Không đổi được coin");
    }
  };

  document.getElementById("logout-btn").onclick = () => location.reload();

  loadSummary();
  loadBots();
  startChart();
  connectWS();
}


// ====================== SUMMARY / BOTS ======================
async function loadSummary() {
  try {
    const data = await apiRequest("/api/summary");
    document.getElementById("status-box").innerHTML = data.summary.replace(/\n/g, "<br>");
  } catch {
    document.getElementById("status-box").innerHTML = "Chưa cấu hình API Binance";
  }
}

async function loadBots() {
  try {
    const data = await apiRequest("/api/bots");
    const html = data.bots.map(b => `
      <div class="card bot-info">
        <b>Bot #${b.bot_id}</b> - ${b.symbol || "-"}
        <button data-id="${b.bot_id}" class="btn btn-secondary btn-stop">Stop</button>
      </div>
    `).join("");
    document.getElementById("bots-box").innerHTML = html;
    document.querySelectorAll(".btn-stop").forEach(btn => {
      btn.onclick = async () => {
        await apiRequest("/api/stop-bot", { method: "POST", body: { bot_id: btn.dataset.id }});
        loadBots();
      }
    });
  } catch {
    document.getElementById("bots-box").innerHTML = "Không có bot.";
  }
}


// ====================== CHART ======================
function startChart() {
  const ctx = document.getElementById("priceChart").getContext("2d");
  priceChart = new Chart(ctx, {
    type: "line",
    data: { labels: labelData, datasets: [{ label: "Price", data: priceData }] },
    options: { responsive: true, animation: false }
  });
}


// ====================== WEBSOCKET ======================
function connectWS() {
  const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/prices";
  ws = new WebSocket(url);
  
  ws.onmessage = (event) => {
    const d = JSON.parse(event.data);
    const timeStr = new Date(d.timestamp * 1000).toLocaleTimeString("vi-VN", { hour12: false });

    // update metric
    document.getElementById("metric-price").textContent   = d.price.toFixed(2);
    document.getElementById("metric-balance").textContent = d.balance.toFixed(2);
    document.getElementById("metric-pnl").textContent     = d.pnl.toFixed(2);
    document.getElementById("metric-bot").textContent     = d.bot_running;

    // update chart
    priceData.push(d.price);
    labelData.push(timeStr);
    if (priceData.length > 50) { priceData.shift(); labelData.shift(); }
    priceChart.update("none");

    // update table
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${timeStr}</td><td>${d.symbol}</td><td>${d.price}</td><td>${d.volume}</td>`;
    const tbody = document.getElementById("ticks-body");
    tbody.prepend(tr);
    if (tbody.rows.length > 15) tbody.deleteRow(tbody.rows.length - 1);
  };

  ws.onclose = () => setTimeout(connectWS, 2000);
}

function reconnectWS() {
  if (ws) ws.close();
  priceData = []; labelData = [];
  connectWS();
}


// ====================== INIT ======================
renderAuthScreen();
