import axios from 'axios';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

export const http = axios.create({ baseURL: API });

http.interceptors.request.use((config) => {
  const t = localStorage.getItem('tkp_token');
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('tkp_token');
      localStorage.removeItem('tkp_user');
    }
    return Promise.reject(err);
  }
);
