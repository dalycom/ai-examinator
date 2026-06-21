"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiRequest, ApiError, loginRequest, logoutRequest, refreshRequest } from "@/lib/api/client";
import type { TokenResponse, UserProfile } from "@/lib/api/types";
import { clearTokens, loadTokens, saveTokens } from "@/lib/auth/storage";

type AuthContextValue = {
  user: UserProfile | null;
  accessToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  authorizedRequest: <T>(path: string, options?: { method?: string; body?: unknown }) => Promise<T>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function applyTokens(tokens: TokenResponse): { accessToken: string; refreshToken: string | null } {
  const accessToken = tokens.access_token;
  const refreshToken = tokens.refresh_token ?? null;
  saveTokens({ accessToken, refreshToken });
  return { accessToken, refreshToken };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMe = useCallback(async (token: string) => {
    return apiRequest<UserProfile>("/auth/me", { accessToken: token });
  }, []);

  const bootstrap = useCallback(async () => {
    const stored = loadTokens();
    if (!stored) {
      setIsLoading(false);
      return;
    }

    try {
      const profile = await fetchMe(stored.accessToken);
      setAccessToken(stored.accessToken);
      setRefreshToken(stored.refreshToken);
      setUser(profile);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && stored.refreshToken) {
        try {
          const tokens = await refreshRequest(stored.refreshToken);
          const next = applyTokens(tokens);
          const profile = await fetchMe(next.accessToken);
          setAccessToken(next.accessToken);
          setRefreshToken(next.refreshToken);
          setUser(profile);
          setIsLoading(false);
          return;
        } catch {
          clearTokens();
        }
      } else {
        clearTokens();
      }
    } finally {
      setIsLoading(false);
    }
  }, [fetchMe]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await loginRequest(email, password);
      if (tokens.mfa_required) {
        throw new Error("MFA is required but not yet supported in the web UI.");
      }

      const next = applyTokens(tokens);
      const profile = await fetchMe(next.accessToken);
      setAccessToken(next.accessToken);
      setRefreshToken(next.refreshToken);
      setUser(profile);
    },
    [fetchMe],
  );

  const logout = useCallback(async () => {
    if (accessToken && refreshToken) {
      try {
        await logoutRequest(accessToken, refreshToken);
      } catch {
        // Clear local session even if server logout fails.
      }
    }

    clearTokens();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }, [accessToken, refreshToken]);

  const authorizedRequest = useCallback(
    async <T,>(path: string, options?: { method?: string; body?: unknown }): Promise<T> => {
      if (!accessToken) {
        throw new ApiError(401, "Not authenticated");
      }

      try {
        return await apiRequest<T>(path, {
          method: options?.method,
          body: options?.body,
          accessToken,
        });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401 || !refreshToken) {
          throw error;
        }

        const tokens = await refreshRequest(refreshToken);
        const next = applyTokens(tokens);
        setAccessToken(next.accessToken);
        setRefreshToken(next.refreshToken);

        return apiRequest<T>(path, {
          method: options?.method,
          body: options?.body,
          accessToken: next.accessToken,
        });
      }
    },
    [accessToken, refreshToken],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isLoading,
      isAuthenticated: Boolean(user && accessToken),
      login,
      logout,
      authorizedRequest,
    }),
    [user, accessToken, isLoading, login, logout, authorizedRequest],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
