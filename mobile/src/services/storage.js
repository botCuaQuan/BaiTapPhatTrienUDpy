import * as SecureStore from 'expo-secure-store';

export const saveCredentials = async (apiKey, apiSecret) => {
  try {
    await SecureStore.setItemAsync('api_key', apiKey);
    await SecureStore.setItemAsync('api_secret', apiSecret);
    return true;
  } catch (error) {
    console.error('Lỗi lưu credentials:', error);
    return false;
  }
};

export const getCredentials = async () => {
  try {
    const apiKey = await SecureStore.getItemAsync('api_key');
    const apiSecret = await SecureStore.getItemAsync('api_secret');
    
    if (apiKey && apiSecret) {
      return { apiKey, apiSecret };
    }
    return null;
  } catch (error) {
    console.error('Lỗi đọc credentials:', error);
    return null;
  }
};

export const clearCredentials = async () => {
  try {
    await SecureStore.deleteItemAsync('api_key');
    await SecureStore.deleteItemAsync('api_secret');
    return true;
  } catch (error) {
    console.error('Lỗi xóa credentials:', error);
    return false;
  }
};
