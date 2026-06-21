export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_BASE_URL}/api/v1`;

/** WebSocket base derived from API URL (http→ws, https→wss). */
export function getWebSocketBaseUrl(): string {
  const apiUrl = API_BASE_URL.replace(/\/$/, "");
  if (apiUrl.startsWith("https://")) {
    return apiUrl.replace("https://", "wss://");
  }
  return apiUrl.replace("http://", "ws://");
}
