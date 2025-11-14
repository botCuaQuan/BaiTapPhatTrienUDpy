import axios from 'axios';

// Thay bằng URL Railway của bạn
const API_BASE_URL = 'https://your-app.railway.app';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Interceptor để log requests
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor để log responses
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.log('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const connectBinance = async (apiKey, apiSecret) => {
  try {
    const response = await api.post('/api/connect', {
      api_key: apiKey,
      api_secret: apiSecret,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Không thể kết nối đến server');
  }
};

export const getSystemInfo = async () => {
  try {
    const response = await api.get('/api/system-info');
    return response.data;
  } catch (error) {
    throw new Error('Không thể lấy thông tin hệ thống');
  }
};

export const getBots = async () => {
  try {
    const response = await api.get('/api/bots');
    return response.data;
  } catch (error) {
    throw new Error('Không thể lấy danh sách bot');
  }
};

export const addBot = async (botConfig) => {
  try {
    const response = await api.post('/api/add-bot', botConfig);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.message || 'Không thể thêm bot');
  }
};

export const stopBot = async (botId) => {
  try {
    const response = await api.post('/api/stop-bot', { bot_id: botId });
    return response.data;
  } catch (error) {
    throw new Error('Không thể dừng bot');
  }
};

export const stopAllBots = async () => {
  try {
    const response = await api.post('/api/stop-bot', { bot_id: 'all' });
    return response.data;
  } catch (error) {
    throw new Error('Không thể dừng tất cả bot');
  }
};

export const getBalance = async () => {
  try {
    const response = await api.get('/api/balance');
    return response.data;
  } catch (error) {
    throw new Error('Không thể lấy số dư');
  }
};

export const getPositions = async () => {
  try {
    const response = await api.get('/api/positions');
    return response.data;
  } catch (error) {
    throw new Error('Không thể lấy vị thế');
  }
};

export default api;
