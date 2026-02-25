import axios from 'axios';

// Resolve API base URL:
// 1. Explicit env var or localStorage override (for mobile/LAN)
// 2. Tauri desktop app → connect to localhost backend
// 3. Otherwise use relative /api (same-origin production or dev proxy)
function resolveBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl.replace(/\/$/, '') + '/api';

  const savedServer = localStorage.getItem('regia_server_url');
  if (savedServer) return savedServer.replace(/\/$/, '') + '/api';

  // Detect Tauri: window.__TAURI__ exists in Tauri v2 apps
  if (typeof window !== 'undefined' && (window as any).__TAURI__) {
    return 'http://localhost:8420/api';
  }

  return '/api';
}

const api = axios.create({
  baseURL: resolveBaseUrl(),
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('regia_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// === Auth ===
export const getAuthStatus = () => api.get('/auth/status');
export const setupUser = (data: any) => api.post('/auth/setup', data);
export const login = (data: any) => api.post('/auth/login', data);
export const logout = () => api.post('/auth/logout');
export const changePassword = (data: any) => api.post('/auth/change-password', data);
export const forgotPassword = (email: string) => api.post('/auth/forgot-password', { email });
export const resetPassword = (token: string, new_password: string) =>
  api.post('/auth/reset-password', { token, new_password });

// === UI Preferences ===
export const getUIPreferences = () => api.get('/ui/preferences');
export const updateUIPreferences = (data: any) => api.put('/ui/preferences', data);

// === Cloud Storage ===
export const getCloudProviders = () => api.get('/cloud-storage/providers');
export const getEmailProviders = () => api.get('/cloud-storage/email-providers');
export const getCloudConnections = () => api.get('/cloud-storage/connections');
export const createCloudConnection = (data: any) => api.post('/cloud-storage/connect', data);
export const deleteCloudConnection = (id: string) => api.delete(`/cloud-storage/connections/${id}`);
export const startOAuth2Flow = (data: any) => api.post('/cloud-storage/oauth2/start', data);
export const getCloudSyncStatus = (id: string) => api.get(`/cloud-storage/sync/${id}/status`);

// === Dashboard ===
export const getDashboard = () => api.get('/dashboard');
export const getHealth = () => api.get('/health');

// === Settings ===
export const getStatus = () => api.get('/settings/status');
export const setupMasterPassword = (password: string) =>
  api.post('/settings/setup', { password });
export const unlock = (password: string) =>
  api.post('/settings/unlock', { password });
export const lock = () => api.post('/settings/lock');
export const getAccounts = () => api.get('/settings/accounts');
export const addAccount = (data: any) => api.post('/settings/accounts', data);
export const deleteAccount = (id: string) => api.delete(`/settings/accounts/${id}`);
export const storeCredentials = (accountId: string, data: any) =>
  api.post(`/settings/accounts/${accountId}/credentials`, data);
export const getConfig = () => api.get('/settings/config');
export const updateConfig = (data: any) => api.put('/settings/config', data);

// === Emails ===
export const getEmails = (params?: any) => api.get('/emails', { params });
export const getEmail = (id: number) => api.get(`/emails/${id}`);
export const triggerFetch = (accountId: string) => api.post(`/emails/fetch/${accountId}`);
export const triggerFetchAll = () => api.post('/emails/fetch-all');
export const getEmailStats = () => api.get('/emails/stats/summary');

// === Documents ===
export const getDocuments = (params?: any) => api.get('/documents', { params });
export const getDocument = (id: number) => api.get(`/documents/${id}`);
export const getDocumentText = (id: number) => api.get(`/documents/${id}/text`);
export const verifyDocument = (id: number) => api.get(`/documents/${id}/verify`);
export const getDocumentStats = () => api.get('/documents/stats/summary');
export const getDocumentPreviewUrl = (id: number, page = 0) =>
  `/api/documents/${id}/preview?page=${page}`;
export const getDocumentDownloadUrl = (id: number) =>
  `/api/documents/${id}/download`;

// === Search ===
export const search = (data: any) => api.post('/search', data);
export const getSuggestions = (q: string) => api.get('/search/suggest', { params: { q } });
export const getClassifications = () => api.get('/search/classifications');
export const getCategories = () => api.get('/search/categories');

// === Agent (Reggie) ===
export const getAgentStatus = () => api.get('/agent/status');
export const chatWithReggie = (data: any) => api.post('/agent/chat', data);
export const getChatHistory = (sessionId: string) => api.get(`/agent/history/${sessionId}`);
export const clearChatHistory = (sessionId: string) => api.delete(`/agent/history/${sessionId}`);
export const getMemories = () => api.get('/agent/memory');
export const deleteMemory = (id: number) => api.delete(`/agent/memory/${id}`);
export const clearAllMemories = () => api.delete('/agent/memory');
export const getKnowledge = () => api.get('/agent/knowledge');
export const clearAllKnowledge = () => api.delete('/agent/knowledge');

// === Files ===
export const browseFiles = (path?: string) =>
  api.get('/files/browse', { params: path ? { path } : {} });
export const getDirectoryTree = (maxDepth = 3) =>
  api.get('/files/tree', { params: { max_depth: maxDepth } });

// === Logs ===
export const getLogs = (params?: any) => api.get('/logs', { params });

// === Email Rules ===
export const getRules = () => api.get('/rules');
export const createRule = (data: any) => api.post('/rules', data);
export const updateRule = (id: number, data: any) => api.put(`/rules/${id}`, data);
export const deleteRule = (id: number) => api.delete(`/rules/${id}`);
export const getRuleFields = () => api.get('/rules/fields');
export const testRules = (emailData: any) => api.post('/rules/test', emailData);

// === Personal Cloud Mode ===
export const getCloudMode = () => api.get('/cloud-mode');
export const getTailscaleStatus = () => api.get('/cloud-mode/tailscale');
export const getWireguardStatus = () => api.get('/cloud-mode/wireguard');

export default api;
