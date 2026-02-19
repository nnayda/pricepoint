import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { loginUser, registerUser, getCurrentUser } from "../services/auth";
import type { AuthUser } from "../services/auth";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tokenRef = useRef<string | null>(null);

  const isAuthenticated = user !== null;

  const refreshAuth = useCallback(async () => {
    const token = tokenRef.current;
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const currentUser = await getCurrentUser(token);
      setUser(currentUser);
    } catch {
      tokenRef.current = null;
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshAuth();
  }, [refreshAuth]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const response = await loginUser(email, password);
      tokenRef.current = response.access_token;
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, displayName: string) => {
    setError(null);
    try {
      const response = await registerUser(email, password, displayName);
      tokenRef.current = response.access_token;
      setUser(response.user);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    tokenRef.current = null;
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      error,
      login,
      register,
      logout,
      refreshAuth,
    }),
    [user, isAuthenticated, isLoading, error, login, register, logout, refreshAuth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
