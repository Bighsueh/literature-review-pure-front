/**
 * API 配置管理
 * 統一管理所有 API 端點和相關設置
 */

// 獲取環境變量的輔助函數
const getEnvVar = (key: string, defaultValue: string): string => {
  return import.meta.env[key] || defaultValue;
};

const getEnvBool = (key: string, defaultValue: boolean = false): boolean => {
  const value = import.meta.env[key];
  if (value === undefined) return defaultValue;
  return value === 'true' || value === '1';
};

const getEnvNumber = (key: string, defaultValue: number): number => {
  const value = import.meta.env[key];
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
};

// API 基礎配置
export const API_CONFIG = {
  // 主要 API 配置
  API_BASE_URL: getEnvVar('VITE_API_BASE_URL', 'http://localhost:28001/api'),
  API_TIMEOUT: getEnvNumber('VITE_API_TIMEOUT', 30000),
  
  // WebSocket 配置
  WS_BASE_URL: getEnvVar('VITE_WS_BASE_URL', 'ws://localhost:28001'),
  
  // Split Sentences 服務配置
  SPLIT_SENTENCES_BASE_URL: getEnvVar('VITE_SPLIT_SENTENCES_BASE_URL', 'http://localhost:28000'),
  
  // 功能開關
  USE_UNIFIED_QUERY: getEnvBool('VITE_USE_UNIFIED_QUERY', false),
  USE_UNIFIED_FILE_PROCESSOR: getEnvBool('VITE_USE_UNIFIED_FILE_PROCESSOR', false),
  DISABLE_DIRECT_N8N: getEnvBool('VITE_DISABLE_DIRECT_N8N', false),
  
  // 開發設置
  DEBUG_MODE: getEnvBool('VITE_DEBUG_MODE', false),
  
  // 環境判斷
  IS_PRODUCTION: import.meta.env.PROD,
  IS_DEVELOPMENT: import.meta.env.DEV,
} as const;

// 獲取完整的 API URL
export const getApiUrl = (endpoint: string = ''): string => {
  const baseUrl = API_CONFIG.API_BASE_URL;
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return cleanEndpoint ? `${baseUrl}/${cleanEndpoint}` : baseUrl;
};

// 獲取 WebSocket URL
export const getWebSocketUrl = (path: string = ''): string => {
  const baseUrl = API_CONFIG.WS_BASE_URL;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${cleanPath}`;
};

// 獲取 Split Sentences URL
export const getSplitSentencesUrl = (): string => {
  // 在生產環境中由 Nginx 處理
  if (API_CONFIG.IS_PRODUCTION) {
    return "";
  }
  return API_CONFIG.SPLIT_SENTENCES_BASE_URL;
};

// 配置驗證
export const validateConfig = (): void => {
  const requiredConfigs = [
    { key: 'API_BASE_URL', value: API_CONFIG.API_BASE_URL },
    { key: 'WS_BASE_URL', value: API_CONFIG.WS_BASE_URL },
  ];

  const missingConfigs = requiredConfigs.filter(config => !config.value);
  
  if (missingConfigs.length > 0) {
    const missing = missingConfigs.map(c => c.key).join(', ');
    throw new Error(`缺少必要的配置: ${missing}`);
  }
};

// 開發時顯示配置信息
export const logConfig = (): void => {
  if (API_CONFIG.IS_DEVELOPMENT && API_CONFIG.DEBUG_MODE) {
    console.group('🔧 API 配置信息');
    console.log('API Base URL:', API_CONFIG.API_BASE_URL);
    console.log('WebSocket URL:', API_CONFIG.WS_BASE_URL);
    console.log('Split Sentences URL:', getSplitSentencesUrl());
    console.log('Timeout:', API_CONFIG.API_TIMEOUT);
    console.log('功能開關:', {
      USE_UNIFIED_QUERY: API_CONFIG.USE_UNIFIED_QUERY,
      USE_UNIFIED_FILE_PROCESSOR: API_CONFIG.USE_UNIFIED_FILE_PROCESSOR,
      DISABLE_DIRECT_N8N: API_CONFIG.DISABLE_DIRECT_N8N,
    });
    console.groupEnd();
  }
};

// 初始化配置
try {
  validateConfig();
  logConfig();
} catch (error) {
  console.error('API 配置錯誤:', error);
}

export default API_CONFIG; 