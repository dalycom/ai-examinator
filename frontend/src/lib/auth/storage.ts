const ACCESS_TOKEN_KEY = "ai_examinator.access_token";
const REFRESH_TOKEN_KEY = "ai_examinator.refresh_token";

export type StoredTokens = {
  accessToken: string;
  refreshToken: string | null;
};

export function loadTokens(): StoredTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  if (!accessToken) {
    return null;
  }

  return {
    accessToken,
    refreshToken: window.localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

export function saveTokens(tokens: { accessToken: string; refreshToken?: string | null }) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  if (tokens.refreshToken) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  }
}

export function clearTokens() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
