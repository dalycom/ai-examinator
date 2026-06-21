"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { API_V1, getWebSocketBaseUrl } from "@/lib/api/config";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  sessionId: string;
  disabled?: boolean;
  onRecordingStarted: () => void;
  onTranscriptReady: () => void;
};

type WsTranscriptSegment = {
  type: "transcript_segment";
  seq: number;
  speaker: string;
  language: string;
  text: string;
  confidence: number;
  start_ms: number;
  end_ms: number;
};

export function AudioRecorder({
  sessionId,
  disabled = false,
  onRecordingStarted,
  onTranscriptReady,
}: Props) {
  const t = useTranslations("consultation");
  const { accessToken, authorizedRequest } = useAuth();
  const [isRecording, setIsRecording] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveSegments, setLiveSegments] = useState<WsTranscriptSegment[]>([]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const seqRef = useRef(0);

  const closeWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => () => closeWebSocket(), [closeWebSocket]);

  const connectWebSocket = useCallback(() => {
    if (!accessToken) {
      return null;
    }

    const wsUrl = `${getWebSocketBaseUrl()}/api/v1/ws/sessions/${sessionId}?token=${encodeURIComponent(accessToken)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStreamStatus(t("wsConnected"));
      ws.send(JSON.stringify({ type: "resume", last_seq: seqRef.current }));
    };

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data as string) as {
        type: string;
        session_status?: string;
        seq?: number;
        speaker?: string;
        language?: string;
        text?: string;
        confidence?: number;
        start_ms?: number;
        end_ms?: number;
      };

      if (payload.type === "status" || payload.type === "resume_ack") {
        setStreamStatus(payload.session_status ?? t("wsConnected"));
        return;
      }

      if (payload.type === "chunk_ack" && payload.seq !== undefined) {
        seqRef.current = payload.seq;
        return;
      }

      if (payload.type === "transcript_segment" && payload.text) {
        const text = payload.text;
        setLiveSegments((current) => [
          ...current,
          {
            type: "transcript_segment",
            seq: payload.seq ?? 0,
            speaker: payload.speaker ?? "doctor",
            language: payload.language ?? "en",
            text,
            confidence: payload.confidence ?? 0,
            start_ms: payload.start_ms ?? 0,
            end_ms: payload.end_ms ?? 0,
          },
        ]);
      }
    };

    ws.onerror = () => setError(t("wsError"));
    ws.onclose = () => setStreamStatus(null);

    return ws;
  }, [accessToken, sessionId, t]);

  const uploadRecording = async (blob: Blob) => {
    const uploadMeta = await authorizedRequest<{
      recording_id: string;
      upload_url: string;
    }>(`/sessions/${sessionId}/audio:create-upload`, {
      method: "POST",
      body: { filename: "consultation.webm", mime_type: blob.type || "audio/webm" },
    });

    const putResponse = await fetch(uploadMeta.upload_url, {
      method: "PUT",
      headers: { "Content-Type": blob.type || "audio/webm" },
      body: blob,
    });
    if (!putResponse.ok) {
      throw new Error(t("uploadFailed"));
    }

    await authorizedRequest(`/sessions/${sessionId}/audio:finalize`, {
      method: "POST",
      body: { size_bytes: blob.size, duration_ms: Math.max(blob.size / 10, 1000) },
    });
  };

  const startRecording = async () => {
    setError(null);
    setLiveSegments([]);

    try {
      await authorizedRequest(`/sessions/${sessionId}/recording:start`, { method: "POST" });
      onRecordingStarted();

      connectWebSocket();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
          seqRef.current += 1;
          wsRef.current?.send(
            JSON.stringify({ type: "audio_chunk", seq: seqRef.current, data: "" }),
          );
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        closeWebSocket();

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size === 0) {
          setError(t("noAudioCaptured"));
          return;
        }

        setStreamStatus(t("processing"));
        await uploadRecording(blob);
        onTranscriptReady();
        setStreamStatus(t("transcriptReady"));
      };

      recorder.start(2000);
      setIsRecording(true);
    } catch (recordError) {
      closeWebSocket();
      setError(recordError instanceof Error ? recordError.message : t("recordingFailed"));
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        {!isRecording ? (
          <button
            type="button"
            disabled={disabled}
            onClick={() => void startRecording()}
            className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {t("recordWithMic")}
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-medium text-white hover:bg-rose-800"
          >
            {t("stopRecording")}
          </button>
        )}
      </div>

      {streamStatus ? <p className="text-sm text-slate-600">{streamStatus}</p> : null}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}

      {liveSegments.length > 0 ? (
        <ul className="space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
          {liveSegments.map((segment) => (
            <li key={`${segment.seq}-${segment.start_ms}`}>
              <span className="font-medium text-teal-800">{segment.speaker}: </span>
              {segment.text}
            </li>
          ))}
        </ul>
      ) : null}

      <p className="text-xs text-slate-500">
        {t("wsEndpoint")}: {API_V1}/ws/sessions/{sessionId}
      </p>
    </div>
  );
}
