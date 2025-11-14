import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  Switch,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { addBot } from '../services/api';

export default function AddBotScreen({ navigation }) {
  const [botMode, setBotMode] = useState('static'); // 'static' or 'dynamic'
  const [symbol, setSymbol] = useState('BTCUSDC');
  const [leverage, setLeverage] = useState('10');
  const [percent, setPercent] = useState('5');
  const [takeProfit, setTakeProfit] = useState('100');
  const [stopLoss, setStopLoss] = useState('50');
  const [roiTrigger, setRoiTrigger] = useState('');
  const [botCount, setBotCount] = useState('1');
  const [isLoading, setIsLoading] = useState(false);

  const handleAddBot = async () => {
    // Validate inputs
    if (botMode === 'static' && !symbol.trim()) {
      Alert.alert('Lỗi', 'Vui lòng nhập symbol cho bot tĩnh');
      return;
    }

    const lev = parseInt(leverage);
    const perc = parseFloat(percent);
    const tp = parseFloat(takeProfit);
    const sl = parseFloat(stopLoss);
    const count = parseInt(botCount);

    if (isNaN(lev) || lev < 1 || lev > 100) {
      Alert.alert('Lỗi', 'Đòn bẩy phải từ 1 đến 100');
      return;
    }

    if (isNaN(perc) || perc < 0.1 || perc > 100) {
      Alert.alert('Lỗi', '% số dư phải từ 0.1 đến 100');
      return;
    }

    if (isNaN(tp) || tp <= 0) {
      Alert.alert('Lỗi', 'Take Profit phải lớn hơn 0');
      return;
    }

    if (isNaN(sl) || sl < 0) {
      Alert.alert('Lỗi', 'Stop Loss phải lớn hơn hoặc bằng 0');
      return;
    }

    if (isNaN(count) || count < 1 || count > 10) {
      Alert.alert('Lỗi', 'Số lượng bot phải từ 1 đến 10');
      return;
    }

    let roi = null;
    if (roiTrigger.trim() !== '') {
      roi = parseFloat(roiTrigger);
      if (isNaN(roi) || roi <= 0) {
        Alert.alert('Lỗi', 'ROI Trigger phải lớn hơn 0');
        return;
      }
    }

    const botConfig = {
      symbol: botMode === 'static' ? symbol : null,
      lev: lev,
      percent: perc,
      tp: tp,
      sl: sl,
      roi_trigger: roi,
      bot_mode: botMode,
      bot_count: count,
    };

    setIsLoading(true);
    try {
      const result = await addBot(botConfig);
      if (result.success) {
        Alert.alert('Thành công', result.message, [
          {
            text: 'OK',
            onPress: () => navigation.goBack()
          }
        ]);
      } else {
        Alert.alert('Lỗi', result.message);
      }
    } catch (error) {
      Alert.alert('Lỗi', error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleBotMode = () => {
    setBotMode(prevMode => prevMode === 'static' ? 'dynamic' : 'static');
  };

  return (
    <LinearGradient colors={['#667eea', '#764ba2']} style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardAvoid}
      >
        <ScrollView 
          contentContainerStyle={styles.scrollContainer}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.form}>

            {/* Bot Mode Switch */}
            <View style={styles.switchContainer}>
              <Text style={styles.switchLabel}>Bot Tĩnh (Coin cố định)</Text>
              <Switch
                value={botMode === 'dynamic'}
                onValueChange={toggleBotMode}
                trackColor={{ false: '#767577', true: '#4CAF50' }}
                thumbColor={botMode === 'dynamic' ? '#fff' : '#f4f3f4'}
              />
              <Text style={styles.switchLabel}>Bot Động (Tự tìm coin)</Text>
            </View>

            {botMode === 'static' ? (
              <View style={styles.inputGroup}>
                <Text style={styles.label}>Symbol (Coin)</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Ví dụ: BTCUSDC, ETHUSDC..."
                  placeholderTextColor="rgba(255,255,255,0.6)"
                  value={symbol}
                  onChangeText={setSymbol}
                  autoCapitalize="characters"
                  autoCorrect={false}
                />
              </View>
            ) : (
              <View style={styles.inputGroup}>
                <Text style={styles.label}>Số lượng bot</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Số bot động cần tạo"
                  placeholderTextColor="rgba(255,255,255,0.6)"
                  value={botCount}
                  onChangeText={setBotCount}
                  keyboardType="number-pad"
                />
                <Text style={styles.note}>Mỗi bot sẽ tự động tìm coin riêng</Text>
              </View>
            )}

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Đòn bẩy</Text>
              <TextInput
                style={styles.input}
                placeholder="Ví dụ: 10, 20, 50..."
                placeholderTextColor="rgba(255,255,255,0.6)"
                value={leverage}
                onChangeText={setLeverage}
                keyboardType="number-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>% Số dư mỗi lệnh</Text>
              <TextInput
                style={styles.input}
                placeholder="Ví dụ: 5, 10, 20..."
                placeholderTextColor="rgba(255,255,255,0.6)"
                value={percent}
                onChangeText={setPercent}
                keyboardType="decimal-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Take Profit (%)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ví dụ: 100, 200..."
                placeholderTextColor="rgba(255,255,255,0.6)"
                value={takeProfit}
                onChangeText={setTakeProfit}
                keyboardType="decimal-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Stop Loss (%)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ví dụ: 50, 100..."
                placeholderTextColor="rgba(255,255,255,0.6)"
                value={stopLoss}
                onChangeText={setStopLoss}
                keyboardType="decimal-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>ROI Trigger (%) - Tùy chọn</Text>
              <TextInput
                style={styles.input}
                placeholder="Để trống nếu không dùng"
                placeholderTextColor="rgba(255,255,255,0.6)"
                value={roiTrigger}
                onChangeText={setRoiTrigger}
                keyboardType="decimal-pad"
              />
              <Text style={styles.note}>Kích hoạt cơ chế chốt lời thông minh khi đạt ROI</Text>
            </View>

            <TouchableOpacity
              style={[styles.button, isLoading && styles.buttonDisabled]}
              onPress={handleAddBot}
              disabled={isLoading}
            >
              {isLoading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.buttonText}>🚀 Tạo Bot</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => navigation.goBack()}
              disabled={isLoading}
            >
              <Text style={styles.cancelButtonText}>↩️ Quay lại</Text>
            </TouchableOpacity>

          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardAvoid: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    padding: 20,
  },
  form: {
    width: '100%',
  },
  switchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    padding: 15,
    borderRadius: 12,
  },
  switchLabel: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 12,
    padding: 16,
    color: 'white',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    fontSize: 16,
  },
  note: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
    marginTop: 4,
    fontStyle: 'italic',
  },
  button: {
    backgroundColor: '#4CAF50',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  buttonDisabled: {
    backgroundColor: 'rgba(76, 175, 80, 0.6)',
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  cancelButton: {
    padding: 16,
    alignItems: 'center',
    marginTop: 12,
  },
  cancelButtonText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 16,
  },
});
