// App.js
import React, { useEffect, useState } from "react";
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import AsyncStorage from "@react-native-async-storage/async-storage";

// 🔧 SỬA DÒNG NÀY: URL backend FastAPI trên Railway
// Ví dụ: const API_BASE = "https://ten-backend-cua-ban.up.railway.app";
const API_BASE = "https://your-backend-on-railway.up.railway.app";

// Helper API: tự thêm header X-Auth-Token nếu có
async function apiRequest(path, { method = "GET", body = null, auth = true, token = null } = {}) {
  const url = API_BASE + path;
  const headers = {
    "Content-Type": "application/json",
  };
  if (auth && token) {
    headers["X-Auth-Token"] = token;
  }
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });
  let data = {};
  try {
    data = await res.json();
  } catch (e) {
    data = {};
  }
  if (!res.ok) {
    throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  }
  return data;
}

export default function App() {
  const [loading, setLoading] = useState(true); // load token, check trạng thái
  const [authToken, setAuthToken] = useState(null);
  const [username, setUsername] = useState(null);
  const [hasApi, setHasApi] = useState(false); // đã cấu hình API Binance chưa?
  const [statusMsg, setStatusMsg] = useState("");

  // Form login/register
  const [authUser, setAuthUser] = useState("");
  const [authPass, setAuthPass] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // Form setup API
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [savingApi, setSavingApi] = useState(false);

  // Dashboard data
  const [summary, setSummary] = useState("");
  const [bots, setBots] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  // Form add bot
  const [botMode, setBotMode] = useState("static");
  const [symbol, setSymbol] = useState("");
  const [lev, setLev] = useState("10");
  const [percent, setPercent] = useState("5");
  const [tp, setTp] = useState("50");
  const [sl, setSl] = useState("0");
  const [roiTrigger, setRoiTrigger] = useState("0");
  const [botCount, setBotCount] = useState("3");
  const [addingBot, setAddingBot] = useState(false);

  // ============ INIT: load token từ AsyncStorage & kiểm tra trạng thái ============
  useEffect(() => {
    const init = async () => {
      try {
        const savedToken = await AsyncStorage.getItem("authToken");
        const savedUsername = await AsyncStorage.getItem("username");
        if (savedToken && savedUsername) {
          // Thử gọi /api/me với token này
          try {
            const me = await apiRequest("/api/me", { auth: true, token: savedToken });
            setAuthToken(savedToken);
            setUsername(me.username || savedUsername);

            // Kiểm tra account-status để biết đã có API Binance chưa
            const status = await apiRequest("/api/account-status", {
              auth: true,
              token: savedToken,
            });
            setHasApi(!!status.configured);
          } catch (err) {
            // Token hết hạn hoặc lỗi → xóa và yêu cầu login
            await AsyncStorage.removeItem("authToken");
            await AsyncStorage.removeItem("username");
            setAuthToken(null);
            setUsername(null);
            setHasApi(false);
          }
        } else {
          setAuthToken(null);
          setUsername(null);
          setHasApi(false);
        }
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Khi đã có token + đã cấu hình API thì tự load dashboard
  useEffect(() => {
    if (authToken && hasApi) {
      loadDashboardData();
    }
  }, [authToken, hasApi]);

  // ============ HÀM TIỆN ÍCH ============

  const handleLogout = async () => {
    setAuthToken(null);
    setUsername(null);
    setHasApi(false);
    setSummary("");
    setBots([]);
    await AsyncStorage.removeItem("authToken");
    await AsyncStorage.removeItem("username");
  };

  const loadDashboardData = async () => {
    if (!authToken) return;
    setRefreshing(true);
    try {
      const s = await apiRequest("/api/summary", { auth: true, token: authToken });
      setSummary(s.summary || "");
      const b = await apiRequest("/api/bots", { auth: true, token: authToken });
      setBots(b.bots || []);
      setStatusMsg("");
    } catch (err) {
      setStatusMsg("Lỗi load dashboard: " + err.message);
    } finally {
      setRefreshing(false);
    }
  };

  // ============ AUTH: ĐĂNG NHẬP / ĐĂNG KÝ ============

  const handleLogin = async () => {
    if (!authUser.trim() || !authPass) {
      setStatusMsg("Không được để trống username/password.");
      return;
    }
    setAuthLoading(true);
    setStatusMsg("");
    try {
      const data = await apiRequest("/api/login", {
        method: "POST",
        body: { username: authUser.trim(), password: authPass },
        auth: false,
      });
      setAuthToken(data.token);
      setUsername(data.username);
      await AsyncStorage.setItem("authToken", data.token);
      await AsyncStorage.setItem("username", data.username);

      // Check xem đã cấu hình API chưa
      const status = await apiRequest("/api/account-status", {
        auth: true,
        token: data.token,
      });
      setHasApi(!!status.configured);
      setStatusMsg("");
    } catch (err) {
      setStatusMsg("Lỗi đăng nhập: " + err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!authUser.trim() || !authPass) {
      setStatusMsg("Không được để trống username/password.");
      return;
    }
    setAuthLoading(true);
    setStatusMsg("");
    try {
      const data = await apiRequest("/api/register", {
        method: "POST",
        body: { username: authUser.trim(), password: authPass },
        auth: false,
      });
      setAuthToken(data.token);
      setUsername(data.username);
      await AsyncStorage.setItem("authToken", data.token);
      await AsyncStorage.setItem("username", data.username);

      // Mới đăng ký thì chắc chắn chưa có API Binance
      setHasApi(false);
      setStatusMsg("Đăng ký thành công, hãy cấu hình API Binance.");
    } catch (err) {
      setStatusMsg("Lỗi đăng ký: " + err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  // ============ CẤU HÌNH API KEY / SECRET ============

  const handleSetupApi = async () => {
    if (!apiKey.trim() || !apiSecret.trim()) {
      setStatusMsg("API Key và Secret không được để trống.");
      return;
    }
    if (!authToken) {
      setStatusMsg("Chưa đăng nhập.");
      return;
    }
    setSavingApi(true);
    setStatusMsg("");
    try {
      await apiRequest("/api/setup-account", {
        method: "POST",
        body: { api_key: apiKey.trim(), api_secret: apiSecret.trim() },
        auth: true,
        token: authToken,
      });
      setHasApi(true);
      setApiKey("");
      setApiSecret("");
      setStatusMsg("Cấu hình API Binance thành công.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi lưu API Binance: " + err.message);
    } finally {
      setSavingApi(false);
    }
  };

  // ============ BOT: THÊM, DỪNG, DỪNG TẤT CẢ ============

  const handleAddBot = async () => {
    if (!authToken) return;
    setAddingBot(true);
    setStatusMsg("");
    try {
      const payload = {
        bot_mode: botMode,
        symbol: symbol,
        lev: Number(lev),
        percent: Number(percent),
        tp: Number(tp),
        sl: Number(sl),
        roi_trigger: Number(roiTrigger || 0),
        bot_count: Number(botCount),
      };
      const res = await apiRequest("/api/add-bot", {
        method: "POST",
        body: payload,
        auth: true,
        token: authToken,
      });
      if (!res.ok) {
        throw new Error("API trả về ok=false");
      }
      setStatusMsg("Tạo bot thành công.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi tạo bot: " + err.message);
    } finally {
      setAddingBot(false);
    }
  };

  const handleStopBot = async (botId) => {
    if (!authToken) return;
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-bot", {
        method: "POST",
        body: { bot_id: botId },
        auth: true,
        token: authToken,
      });
      setStatusMsg(`Đã dừng bot: ${botId}`);
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng bot: " + err.message);
    }
  };

  const handleStopAllBots = async () => {
    if (!authToken) return;
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-all-bots", {
        method: "POST",
        auth: true,
        token: authToken,
      });
      setStatusMsg("Đã dừng tất cả bot.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng tất cả bot: " + err.message);
    }
  };

  const handleStopAllCoins = async () => {
    if (!authToken) return;
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-all-coins", {
        method: "POST",
        auth: true,
        token: authToken,
      });
      setStatusMsg("Đã dừng toàn bộ coin.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng toàn bộ coin: " + err.message);
    }
  };

  // ============ RENDER UI ============

  if (loading) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 8, color: "#e5e7eb" }}>Đang tải trạng thái tài khoản...</Text>
        <StatusBar style="light" />
      </SafeAreaView>
    );
  }

  // Chưa đăng nhập → màn hình login/register
  if (!authToken || !username) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.title}>🔐 Đăng nhập / Đăng ký</Text>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Tài khoản</Text>
            {statusMsg ? (
              <Text
                style={[
                  styles.status,
                  statusMsg.startsWith("Lỗi") ? styles.statusErr : styles.statusOk,
                ]}
              >
                {statusMsg}
              </Text>
            ) : null}

            <Text style={styles.label}>Username</Text>
            <TextInput
              style={styles.input}
              value={authUser}
              onChangeText={setAuthUser}
              placeholder="Nhập username"
              placeholderTextColor="#6b7280"
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={authPass}
              onChangeText={setAuthPass}
              placeholder="Nhập password"
              placeholderTextColor="#6b7280"
            />

            <View style={[styles.row, { marginTop: 12 }]}>
              <TouchableOpacity
                style={[styles.button, styles.buttonPrimary, { flex: 1 }]}
                onPress={handleLogin}
                disabled={authLoading}
              >
                {authLoading ? (
                  <ActivityIndicator color="#0f172a" />
                ) : (
                  <Text style={styles.buttonText}>Đăng nhập</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.button, styles.buttonSecondary, { flex: 1 }]}
                onPress={handleRegister}
                disabled={authLoading}
              >
                {authLoading ? (
                  <ActivityIndicator color="#e5e7eb" />
                ) : (
                  <Text style={[styles.buttonText, { color: "#e5e7eb" }]}>
                    Đăng ký & đăng nhập
                  </Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
        <StatusBar style="light" />
      </SafeAreaView>
    );
  }

  // Đã login nhưng chưa cấu hình API Binance
  if (!hasApi) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.title}>⚙️ Cấu hình API Binance</Text>
          <Text style={styles.subtitle}>User: {username}</Text>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>🔑 Nhập API Key & Secret</Text>
            {statusMsg ? (
              <Text
                style={[
                  styles.status,
                  statusMsg.startsWith("Lỗi") ? styles.statusErr : styles.statusOk,
                ]}
              >
                {statusMsg}
              </Text>
            ) : null}

            <Text style={styles.label}>API Key</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={apiKey}
              onChangeText={setApiKey}
              placeholder="Nhập API Key"
              placeholderTextColor="#6b7280"
            />

            <Text style={styles.label}>API Secret</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={apiSecret}
              onChangeText={setApiSecret}
              placeholder="Nhập API Secret"
              placeholderTextColor="#6b7280"
            />

            <View style={[styles.row, { marginTop: 16 }]}>
              <TouchableOpacity
                style={[styles.button, styles.buttonPrimary, { flex: 2 }]}
                onPress={handleSetupApi}
                disabled={savingApi}
              >
                {savingApi ? (
                  <ActivityIndicator color="#0f172a" />
                ) : (
                  <Text style={styles.buttonText}>Lưu API & khởi tạo bot</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.button, styles.buttonDanger, { flex: 1 }]}
                onPress={handleLogout}
              >
                <Text style={styles.buttonText}>Đăng xuất</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.note}>
              Mỗi tài khoản đăng nhập có API & bot riêng, web và app mobile dùng chung backend.
            </Text>
          </View>
        </ScrollView>
        <StatusBar style="light" />
      </SafeAreaView>
    );
  }

  // Đã login + đã có API → Dashboard bot
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>🤖 Trading Bot – Mobile</Text>
        <Text style={styles.subtitle}>User: {username}</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>📊 Thống kê nhanh</Text>
          {statusMsg ? (
            <Text
              style={[
                styles.status,
                statusMsg.startsWith("Lỗi") ? styles.statusErr : styles.statusOk,
              ]}
            >
              {statusMsg}
            </Text>
          ) : null}
          {refreshing ? (
            <ActivityIndicator style={{ marginVertical: 8 }} />
          ) : (
            <Text style={styles.pre}>{summary || "Chưa có dữ liệu."}</Text>
          )}
          <View style={styles.row}>
            <TouchableOpacity
              style={[styles.button, styles.buttonSecondary, { flex: 1 }]}
              onPress={loadDashboardData}
              disabled={refreshing}
            >
              <Text style={[styles.buttonText, { color: "#e5e7eb" }]}>
                🔄 Refresh
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.buttonDanger, { flex: 1 }]}
              onPress={handleLogout}
            >
              <Text style={styles.buttonText}>Đăng xuất</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>➕ Tạo bot mới</Text>

          <Text style={styles.label}>Chế độ bot</Text>
          <View style={styles.row}>
            <TouchableOpacity
              style={[
                styles.chip,
                botMode === "static" ? styles.chipActive : null,
              ]}
              onPress={() => setBotMode("static")}
            >
              <Text style={styles.chipText}>Static</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.chip,
                botMode === "dynamic" ? styles.chipActive : null,
              ]}
              onPress={() => setBotMode("dynamic")}
            >
              <Text style={styles.chipText}>Dynamic</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.note}>
            Dynamic: để trống Symbol, bot tự chọn coin theo RSI + volume.
          </Text>

          <Text style={styles.label}>Symbol (ví dụ: XRPUSDC)</Text>
          <TextInput
            style={styles.input}
            value={symbol}
            onChangeText={setSymbol}
            placeholder="XRPUSDC (để trống nếu Dynamic)"
            placeholderTextColor="#6b7280"
          />

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>Đòn bẩy (leverage)</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={lev}
                onChangeText={setLev}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>% số dư / lệnh</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={percent}
                onChangeText={setPercent}
              />
            </View>
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>TP %</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={tp}
                onChangeText={setTp}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>SL % (0 = tắt)</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={sl}
                onChangeText={setSl}
              />
            </View>
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>ROI trigger % (0 = tắt)</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={roiTrigger}
                onChangeText={setRoiTrigger}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>Số coin tối đa</Text>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={botCount}
                onChangeText={setBotCount}
              />
            </View>
          </View>

          <TouchableOpacity
            style={[styles.button, styles.buttonPrimary, { marginTop: 12 }]}
            onPress={handleAddBot}
            disabled={addingBot}
          >
            {addingBot ? (
              <ActivityIndicator color="#0f172a" />
            ) : (
              <Text style={styles.buttonText}>🚀 Tạo bot</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>📋 Danh sách bot</Text>
          {bots.length === 0 ? (
            <Text style={styles.note}>Chưa có bot nào.</Text>
          ) : (
            bots.map((b) => (
              <View key={b.bot_id} style={styles.botCard}>
                <Text style={styles.botTitle}>🤖 {b.bot_id}</Text>
                <Text style={styles.botInfo}>
                  Mode: {b.mode} • Coins: {b.active_coins}/{b.max_coins}
                </Text>
                <TouchableOpacity
                  style={[styles.button, styles.buttonDanger, { marginTop: 4 }]}
                  onPress={() => handleStopBot(b.bot_id)}
                >
                  <Text style={styles.buttonText}>⛔ Dừng bot này</Text>
                </TouchableOpacity>
              </View>
            ))
          )}
          <View style={styles.row}>
            <TouchableOpacity
              style={[styles.button, styles.buttonDanger, { flex: 1 }]}
              onPress={handleStopAllBots}
            >
              <Text style={styles.buttonText}>🛑 Dừng TẤT CẢ bot</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.buttonSecondary, { flex: 1 }]}
              onPress={handleStopAllCoins}
            >
              <Text style={[styles.buttonText, { color: "#e5e7eb" }]}>
                ⛔ Dừng toàn bộ COIN
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}

// ============ STYLES ============

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#020617",
  },
  center: {
    flex: 1,
    backgroundColor: "#020617",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#facc15",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: "#9ca3af",
    marginBottom: 12,
  },
  card: {
    backgroundColor: "#020617",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#1f2937",
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#facc15",
    marginBottom: 8,
  },
  label: {
    fontSize: 13,
    color: "#e5e7eb",
    marginTop: 8,
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#4b5563",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    color: "#e5e7eb",
    fontSize: 14,
  },
  button: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonPrimary: {
    backgroundColor: "#22c55e",
  },
  buttonDanger: {
    backgroundColor: "#ef4444",
  },
  buttonSecondary: {
    backgroundColor: "#1f2937",
  },
  buttonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#0f172a",
  },
  status: {
    fontSize: 13,
    marginBottom: 6,
  },
  statusOk: {
    color: "#22c55e",
  },
  statusErr: {
    color: "#f97373",
  },
  note: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 6,
  },
  pre: {
    fontSize: 13,
    color: "#e5e7eb",
    marginVertical: 8,
  },
  row: {
    flexDirection: "row",
    gap: 8,
    marginTop: 4,
    marginBottom: 4,
  },
  chip: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#4b5563",
    alignItems: "center",
  },
  chipActive: {
    backgroundColor: "#1f2937",
  },
  chipText: {
    fontSize: 13,
    color: "#e5e7eb",
  },
  botCard: {
    borderWidth: 1,
    borderColor: "#1f2937",
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  botTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#e5e7eb",
  },
  botInfo: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 2,
  },
});
