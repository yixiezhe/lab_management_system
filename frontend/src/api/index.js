// frontend/src/api/index.js
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';

const apiClient = axios.create({
  // 这里固定为后端前缀 /api
  baseURL: '/api',
});

// --- 请求拦截器 ---
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    const token = authStore.accessToken;

    // ✅ 防呆：如果你把 url 写成了 "/api/xxx"，自动去掉开头的 "/api"
    // 避免拼成 "/api/api/xxx"
    if (typeof config.url === 'string' && config.url.startsWith('/api/')) {
      config.url = config.url.replace(/^\/api/, '');
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (config.method === 'get') {
      config.params = { ...config.params, _t: new Date().getTime() };
    }

    return config;
  },
  (error) => {
    console.error("Request Interceptor Error:", error);
    return Promise.reject(error);
  }
);

// --- 响应拦截器（你的逻辑保留） ---
let isRefreshing = false;
let failedQueue = [];

const isKioskDeviceLoginContext = () => {
  try {
    const params = new URLSearchParams(window.location.search || '');
    if (params.get('kiosk_mode') !== 'true') return false;
    if (params.get('device_secret')) return true;
    const payload = sessionStorage.getItem('LIMS_DEVICE_LOGIN_PAYLOAD_V1');
    return !!payload;
  } catch {
    return false;
  }
};

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const authStore = useAuthStore();

    console.error("Response Interceptor Error:", error);
    if (error.response) {
      console.error("Error Response Details:", {
        status: error.response.status,
        data: error.response.data,
        url: originalRequest?.url
      });
    } else if (error.request) {
      console.error("Request Sent But No Response:", error.request);
    } else {
      console.error("Request Setup Error:", error.message);
    }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = 'Bearer ' + token;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        if (!authStore.refreshToken) {
          processQueue(error, null);
          if (isKioskDeviceLoginContext()) {
            authStore.clearTokensSilently();
            return Promise.reject(error);
          }
          authStore.logout();
          ElMessage.error('会话已过期，请重新登录。');
          return Promise.reject(error);
        }
        // 注意：这里不要写 /api/token/refresh/，写 /token/refresh/ 就行
        const refreshResponse = await apiClient.post('/token/refresh/', {
          refresh: authStore.refreshToken
        });
        const newAccessToken = refreshResponse.data.access;
        authStore.setAccessToken(newAccessToken);

        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        processQueue(null, newAccessToken);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        if (isKioskDeviceLoginContext()) {
          authStore.clearTokensSilently();
        } else {
          authStore.logout();
          ElMessage.error('会话已过期，请重新登录。');
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
