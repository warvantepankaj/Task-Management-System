import { createContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { STORAGE_KEYS } from '../utils/constants';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session from localStorage. The axios interceptor in services/api.js
    // reads the access token directly each request — no need to set defaults here.
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS);
    const userData = localStorage.getItem(STORAGE_KEYS.USER);

    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch {
        // Corrupted JSON — clear and stay logged out.
        localStorage.removeItem(STORAGE_KEYS.USER);
      }
    }
    setLoading(false);
  }, []);

  const login = (userData, accessToken, refreshToken) => {
    localStorage.setItem(STORAGE_KEYS.ACCESS, accessToken);
    if (refreshToken) localStorage.setItem(STORAGE_KEYS.REFRESH, refreshToken);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
    setUser(userData);
  };

  const logout = async () => {
    const refresh = localStorage.getItem(STORAGE_KEYS.REFRESH);
    // Best-effort server-side revocation. We don't block the UI on it.
    if (refresh) {
      try {
        await authAPI.logout(refresh);
      } catch {
        /* ignore */
      }
    }
    localStorage.removeItem(STORAGE_KEYS.ACCESS);
    localStorage.removeItem(STORAGE_KEYS.REFRESH);
    localStorage.removeItem(STORAGE_KEYS.USER);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
