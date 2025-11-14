import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Image,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { connectBinance } from '../services/api';
import { saveCredentials, getCredentials } from '../services/storage';

export default function LoginScreen({ navigation }) {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingStorage, setIsCheckingStorage] = useState(true);

  useEffect(() => {
    checkStoredCredentials();
  }, []);

  const checkStoredCredentials = async () => {
    try {
      const credentials = await getCredentials();
      if (credentials) {
        setApiKey(credentials.apiKey);
        setApiSecret(credentials.apiSecret);
        // Tự động kết nối nếu có credentials lưu trữ
        // handleConnect(credentials.apiKey, credentials.apiSecret);
      }
    } catch (error) {
      console.error('Lỗi kiểm tra credentials:', error);
    } finally {
      setIsCheckingStorage(false);
    }
  };

  const handleConnect = async (storedApiKey = null, storedApiSecret = null) => {
    const currentApiKey = storedApiKey || apiKey;
    const currentApiSecret = storedApiSecret || apiSecret;

    if (!currentApiKey.trim() || !currentApiSecret.trim()) {
      Alert.alert('Lỗi', 'Vui lòng nhập API Key và Secret');
      return;
    }

    setIsLoading(true);
    try {
      const result = await connectBinance(currentApiKey, currentApiSecret);
      
      if (result.success) {
        // Lưu credentials
        await saveCredentials(currentApiKey, currentApiSecret);
        
        Alert.alert('Thành công', result.message, [
          {
            text: 'Tiếp tục',
            onPress: () => {
              navigation.replace('Dashboard', {
                credentials: { 
                  apiKey: currentApiKey, 
                  apiSecret: currentApiSecret 
                }
              });
            }
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

  const handleClearStorage = async () => {
    Alert.alert(
      'Xác nhận',
      'Bạn có muốn xóa thông tin API đã lưu?',
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa',
          style: 'destructive',
          onPress: async () => {
            const { clearCredentials } = await import('../services/storage');
            await clearCredentials();
            setApiKey('');
            setApiSecret('');
            Alert.alert('Thành công', 'Đã xóa thông tin API');
          }
        }
      ]
    );
  };

  if (isCheckingStorage) {
    return (
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="white" />
        <Text style={styles.loadingText}>Đang tải...</Text>
      </LinearGradient>
    );
  }

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
          <View style={styles.header}>
            <Text style={styles.logo}>🤖</Text>
            <Text style={styles.title}>Trading Bot</Text>
            <Text style={styles.subtitle}>Kết nối Binance Futures</Text>
          </View>

          <View style={styles.form}>
            <TextInput
              style={styles.input}
              placeholder="Binance API Key"
              placeholderTextColor="rgba(255,255,255,0.7)"
              value={apiKey}
              onChangeText={setApiKey}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isLoading}
              autoComplete="off"
            />

            <TextInput
              style={styles.input}
              placeholder="Binance API Secret"
              placeholderTextColor="rgba(255,255,255,0.7)"
              value={apiSecret}
              onChangeText={setApiSecret}
              secureTextEntry
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isLoading}
              autoComplete="off"
            />

            <TouchableOpacity
              style={[styles.button, isLoading && styles.buttonDisabled]}
              onPress={() => handleConnect()}
              disabled={isLoading}
            >
              {isLoading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.buttonText}>🔗 Kết nối Binance</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.clearButton}
              onPress={handleClearStorage}
              disabled={isLoading}
            >
              <Text style={styles.clearButtonText}>🗑️ Xóa thông tin đã lưu</Text>
            </TouchableOpacity>

            <View style={styles.infoBox}>
              <Text style={styles.infoTitle}>ℹ️ Hướng dẫn:</Text>
              <Text style={styles.infoText}>• Tạo API Key trên Binance với quyền Futures Trading</Text>
              <Text style={styles.infoText}>• Bật Enable Reading và Enable Spot & Margin Trading</Text>
              <Text style={styles.infoText}>• Không cần Enable Withdrawals để đảm bảo an toàn</Text>
              <Text style={styles.infoText}>• Thông tin được lưu an toàn trên thiết bị của bạn</Text>
            </View>
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
  keyboardAvoid: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logo: {
    fontSize: 72,
    marginBottom: 24,
  },
  title: {
    fontSize: 32,
    color: 'white',
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
  },
  form: {
    width: '100%',
  },
  input: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 12,
    padding: 16,
    color: 'white',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    fontSize: 16,
  },
  button: {
    backgroundColor: '#4CAF50',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 8,
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
  clearButton: {
    padding: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  clearButtonText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 14,
  },
  infoBox: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 16,
    marginTop: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#4CAF50',
  },
  infoTitle: {
    color: 'white',
    fontWeight: 'bold',
    marginBottom: 8,
    fontSize: 16,
  },
  infoText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 12,
    marginBottom: 4,
    lineHeight: 16,
  },
});
