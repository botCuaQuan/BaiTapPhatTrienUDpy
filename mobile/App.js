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

// 🔧 SỬA DÒNG NÀY: URL backend FastAPI (PHẦN 1) trên Railway
// Ví dụ: const API_BASE = "https://ten-backend-cua-ban.up.railway.app";
const API_BASE = "https://your-backend-on-railway.up.railway.app";

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
  let data = {};
  try {
    data = await res.json();
  } catch (e) {
    data = {};
  }
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  // Form setup account
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [savingAccount, setSavingAccount] = useState(false);

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

  // Lần đầu: kiểm tra backend đã cấu hình API chưa
  useEffect(() => {
    const init = async () => {
      try {
        const status = await apiRequest("/api/account-status");
        setConfigured(!!status.configured);
      } catch (err) {
        setStatusMsg("Không kết nối được backend: " + err.message);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Lấy summary + bots
  const loadDashboardData = async () => {
    setRefreshing(true);
    try {
      const s = await apiRequest("/api/summary");
      setSummary(s.summary || "");

      const b = await apiRequest("/api/bots");
      setBots(b.bots || []);
      setStatusMsg("");
    } catch (err) {
      setStatusMsg("Lỗi load dashboard: " + err.message);
    } finally {
      setRefreshing(false);
    }
  };

  // Khi đã configured rồi thì load data
  useEffect(() => {
    if (configured) {
      loadDashboardData();
    }
  }, [configured]);

  // Setup account
  const handleSetupAccount = async () => {
    if (!apiKey.trim() || !apiSecret.trim()) {
      setStatusMsg("API Key và Secret không được để trống.");
      return;
    }
    setSavingAccount(true);
    setStatusMsg("");
    try {
      await apiRequest("/api/setup-account", {
        method: "POST",
        body: JSON.stringify({
          api_key: apiKey.trim(),
          api_secret: apiSecret.trim(),
        }),
      });
      setConfigured(true);
      setApiKey("");
      setApiSecret("");
      setStatusMsg("Cấu hình tài khoản thành công.");
    } catch (err) {
      setStatusMsg("Lỗi lưu tài khoản: " + err.message);
    } finally {
      setSavingAccount(false);
    }
  };

  // Add bot
  const handleAddBot = async () => {
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
        body: JSON.stringify(payload),
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

  // Stop 1 bot
  const handleStopBot = async (botId) => {
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-bot", {
        method: "POST",
        body: JSON.stringify({ bot_id: botId }),
      });
      setStatusMsg(`Đã dừng bot: ${botId}`);
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng bot: " + err.message);
    }
  };

  // Stop all bots
  const handleStopAllBots = async () => {
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-all-bots", {
        method: "POST",
      });
      setStatusMsg("Đã dừng tất cả bot.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng tất cả bot: " + err.message);
    }
  };

  // Stop all coins
  const handleStopAllCoins = async () => {
    setStatusMsg("");
    try {
      await apiRequest("/api/stop-all-coins", {
        method: "POST",
      });
      setStatusMsg("Đã dừng toàn bộ coin.");
      await loadDashboardData();
    } catch (err) {
      setStatusMsg("Lỗi dừng toàn bộ coin: " + err.message);
    }
  };

  // ======================= UI =======================

  if (loading) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator size="large" color="#facc15" />
        <Text style={{ marginTop: 8, color: "#e5e7eb" }}>
          Đang kiểm tra trạng thái backend...
        </Text>
        <StatusBar style="light" />
      </SafeAreaView>
    );
  }

  // Màn hình cấu hình tài khoản (chưa có API key/secret)
  if (!configured) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.title}>⚙️ Cấu hình tài khoản Binance Futures</Text>
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

            <TouchableOpacity
              style={[styles.button, styles.buttonPrimary, { marginTop: 16 }]}
              onPress={handleSetupAccount}
              disabled={savingAccount}
            >
              {savingAccount ? (
                <ActivityIndicator color="#0f172a" />
              ) : (
                <Text style={styles.buttonText}>Lưu & Khởi tạo Bot Manager</Text>
              )}
            </TouchableOpacity>

            <Text style={styles.note}>
              Lưu ý: API/Secret chỉ lưu trên server backend (RAM), app mobile không lưu trữ.
            </Text>
          </View>
        </ScrollView>
        <StatusBar style="light" />
      </SafeAreaView>
    );
  }

  // Màn hình dashboard (đã có tài khoản)
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>🤖 Trading Bot – Mobile UI</Text>
        <Text style={styles.subtitle}>
          Điều khiển bot Binance Futures trực tiếp từ điện thoại.
        </Text>

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
            <ActivityIndicator color="#facc15" style={{ marginVertical: 8 }} />
          ) : (
            <Text style={styles.pre}>{summary || "Chưa có dữ liệu."}</Text>
          )}
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary]}
            onPress={loadDashboardData}
            disabled={refreshing}
          >
            <Text style={styles.buttonText}>🔄 Refresh summary</Text>
          </TouchableOpacity>
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
              <Text style={styles.buttonText}>⛔ Dừng toàn bộ COIN</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}

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
