import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api, { tokenStore } from "../api/client";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const loadMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch {
      tokenStore.clear();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tokenStore.get()) loadMe();
  }, [loadMe]);

  const login = async ({ role, identifier, password }) => {
    const { data } = await api.post("/auth/login", { role, identifier, password });
    tokenStore.set(data.access_token);
    return loadMe();
  };

  const logout = () => {
    tokenStore.clear();
    setUser(null);
  };

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading]); // eslint-disable-line
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Where each role lands after sign-in.
export const homeFor = (role) => (role === "student" ? "/student" : "/staff");
