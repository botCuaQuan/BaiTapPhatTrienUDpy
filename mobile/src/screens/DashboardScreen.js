import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { getSystemInfo, getBots, stopBot, stopAllBots, getBalance } from '../services/api';

const { width } = Dimensions.get('window');

export default function DashboardScreen({ route, navigation }) {
  const { credentials } = route.params || {};
  const [systemInfo, setSystemInfo] = useState({});
  const [bots, setBots] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState('');

  const loadData = async () => {
    try {
      const [systemData, botsData, balanceData] = await Promise.all([
        getSystemInfo(),
        getBots(),
        getBalance()
      ]);
      
      setSystemInfo({
        ...systemData,
        balance: balanceData.balance
      });
      setBots(botsData);
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (error) {
      Alert.alert('Lỗi', error.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    
    // Refresh mỗi 10 giây
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleStopBot = async (botId, botName) => {
    Alert.alert(
      'Xác nhận dừng bot',
      `Bạn có chắc muốn dừng bot "${botName}"?`,
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Dừng bot',
          style: 'destructive',
          onPress: async () => {
            try {
              await stopBot(botId);
              Alert.alert('Thành công', 'Bot đã được dừng');
              loadData();
            } catch (error) {
              Alert.alert('Lỗi', error.message);
            }
          },
        },
      ]
    );
  };

  const handleStopAll = () => {
    if (bots.length === 0) {
      Alert.alert('Thông báo', 'Không có bot nào đang chạy');
      return;
    }

    Alert.alert(
      'Xác nhận dừng tất cả',
      `Bạn có chắc muốn dừng TẤT CẢ ${bots.length} bot?`,
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Dừng tất cả',
          style: 'destructive',
          onPress: async () => {
            try {
              await stopAllBots();
              Alert.alert('Thành công', 'Tất cả bot đã được dừng');
              loadData();
            } catch (error) {
              Alert.alert('Lỗi', error.message);
            }
          },
        },
      ]
    );
  };

  const handleAddBot = () => {
    navigation.navigate('AddBot');
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return '#4CAF50';
      case 'waiting': return '#FFC107';
      case 'searching': return '#FF9800';
      default: return '#9E9E9E';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'open': return '🟢 Đang trade';
      case 'waiting': return '🟡 Chờ tín hiệu';
      case 'searching': return '🔍 Tìm coin';
      default: return '⚪ Unknown';
    }
  };

  if (loading) {
    return (
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="white" />
        <Text style={styles.loadingText}>Đang tải dữ liệu...</Text>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={['#667eea', '#764ba2']} style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContainer}
        refreshControl={
          <RefreshControl 
            refreshing={refreshing} 
            onRefresh={onRefresh} 
            tintColor="white"
            colors={['white']}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header với số dư */}
        <View style={styles.header}>
          <View style={styles.balanceContainer}>
            <Text style={styles.balanceLabel}>Số dư khả dụng</Text>
            <Text style={styles.balance}>
              ${systemInfo.balance?.toFixed(2) || '0.00'}
            </Text>
          </View>
          <View style={styles.headerButtons}>
            <TouchableOpacity style={styles.addButton} onPress={handleAddBot}>
              <Text style={styles.addButtonText}>➕</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.stopAllButton} onPress={handleStopAll}>
              <Text style={styles.stopAllText}>⛔ Tất cả</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{systemInfo.total_bots || 0}</Text>
            <Text style={styles.statLabel}>Tổng bot</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: '#4CAF50' }]}>
              {systemInfo.trading_bots || 0}
            </Text>
            <Text style={styles.statLabel}>Đang trade</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{systemInfo.searching_bots || 0}</Text>
            <Text style={styles.statLabel}>Đang tìm</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[
              styles.statValue, 
              (systemInfo.total_unrealized_pnl || 0) >= 0 ? styles.positive : styles.negative
            ]}>
              ${systemInfo.total_unrealized_pnl?.toFixed(2) || '0.00'}
            </Text>
            <Text style={styles.statLabel}>Tổng PnL</Text>
          </View>
        </View>

        {/* Last update */}
        <Text style={styles.lastUpdate}>
          Cập nhật: {lastUpdate}
        </Text>

        {/* Bot List */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>🤖 Bot đang chạy</Text>
            <Text style={styles.botCount}>({bots.length})</Text>
          </View>
          
          {bots.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>🤖</Text>
              <Text style={styles.emptyText}>Chưa có bot nào đang chạy</Text>
              <Text style={styles.emptySubtext}>Thêm bot mới để bắt đầu giao dịch</Text>
              <TouchableOpacity style={styles.emptyButton} onPress={handleAddBot}>
                <Text style={styles.emptyButtonText}>➕ Thêm bot đầu tiên</Text>
              </TouchableOpacity>
            </View>
          ) : (
            bots.map((bot) => (
              <View key={bot.bot_id} style={styles.botCard}>
                <View style={styles.botHeader}>
                  <View style={styles.botInfo}>
                    <Text style={styles.botSymbol} numberOfLines={1}>
                      {bot.symbol || 'Đang tìm coin...'}
                    </Text>
                    <Text style={styles.botId} numberOfLines={1}>
                      {bot.bot_id}
                    </Text>
                  </View>
                  <View style={[
                    styles.statusBadge,
                    { backgroundColor: getStatusColor(bot.status) + '40' }
                  ]}>
                    <Text style={styles.statusText}>
                      {getStatusText(bot.status)}
                    </Text>
                  </View>
                </View>

                <View style={styles.botDetails}>
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Đòn bẩy: </Text>
                    <Text style={styles.detailValue}>{bot.lev}x</Text>
                    <Text style={styles.detailLabel}> • Vốn: </Text>
                    <Text style={styles.detailValue}>{bot.percent}%</Text>
                  </View>
                  
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>TP/SL: </Text>
                    <Text style={styles.detailValue}>{bot.tp}%/{bot.sl}%</Text>
                    {bot.roi_trigger && (
                      <>
                        <Text style={styles.detailLabel}> • ROI: </Text>
                        <Text style={styles.detailValue}>{bot.roi_trigger}%</Text>
                      </>
                    )}
                  </View>
                  
                  {bot.entry && bot.current_price && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Giá: </Text>
                      <Text style={styles.detailValue}>{bot.entry.toFixed(4)}</Text>
                      <Text style={styles.detailLabel}> → </Text>
                      <Text style={[
                        styles.detailValue,
                        bot.current_price > bot.entry ? styles.positive : styles.negative
                      ]}>
                        {bot.current_price.toFixed(4)}
                      </Text>
                    </View>
                  )}
                  
                  {bot.average_down_count > 0 && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Số lần nhồi: </Text>
                      <Text style={styles.detailValue}>{bot.average_down_count}</Text>
                    </View>
                  )}
                </View>

                <TouchableOpacity
                  style={styles.stopButton}
                  onPress={() => handleStopBot(bot.bot_id, bot.symbol || 'Unknown')}
                >
                  <Text style={styles.stopButtonText}>⛔ Dừng bot</Text>
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        {/* Thêm padding ở cuối */}
        <View style={styles.bottomPadding} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: 'white',
    marginTop: 16,
    fontSize: 16,
  },
  scrollContainer: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  balanceContainer: {
    flex: 1,
  },
  balanceLabel: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 14,
    marginBottom: 4,
  },
  balance: {
    fontSize: 32,
    color: 'white',
    fontWeight: 'bold',
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  addButton: {
    backgroundColor: '#4CAF50',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  stopAllButton: {
    backgroundColor: 'rgba(244, 67, 54, 0.8)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
  },
  stopAllText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  statCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    width: (width - 48) / 2,
    marginBottom: 12,
  },
  statValue: {
    fontSize: 20,
    color: 'white',
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 12,
  },
  positive: {
    color: '#4CAF50',
  },
  negative: {
    color: '#f44336',
  },
  lastUpdate: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 20,
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 20,
    color: 'white',
    fontWeight: 'bold',
  },
  botCount: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 16,
  },
  emptyState: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 40,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtext: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
  },
  emptyButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  emptyButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  botCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  botHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  botInfo: {
    flex: 1,
    marginRight: 12,
  },
  botSymbol: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
    marginBottom: 4,
  },
  botId: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  botDetails: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    flexWrap: 'wrap',
  },
  detailLabel: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
    fontWeight: '500',
  },
  detailValue: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  stopButton: {
    backgroundColor: 'rgba(244, 67, 54, 0.8)',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  stopButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  bottomPadding: {
    height: 20,
  },
});
