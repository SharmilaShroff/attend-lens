import axios from "axios";

const TOKEN_KEY = "rollcall_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });

api.interceptors.request.use((config) => {
  const t = tokenStore.get();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// An expired/invalid token anywhere sends the user back to the role picker.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !err.config.url.includes("/auth/login")) {
      tokenStore.clear();
      window.location.assign("/");
    }
    return Promise.reject(err);
  }
);

export const errorMessage = (err, fallback = "Something went wrong") =>
  err?.response?.data?.detail && typeof err.response.data.detail === "string"
    ? err.response.data.detail
    : fallback;

export default api;
