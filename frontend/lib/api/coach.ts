// ── Coach API — SSE streaming + history ───────────────────────────────────────

import type { CoachSession, CoachSSEEvent } from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("track_token");
}

// ── History ───────────────────────────────────────────────────────────────────

export async function getCoachHistory(limit = 40): Promise<CoachSession> {
  const token = getToken();
  const res = await fetch(
    `${BASE_URL}/api/v1/coach/history?limit=${limit}`,
    {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );
  if (!res.ok) throw new Error(`Failed to load history: ${res.status}`);
  return res.json();
}

export async function clearCoachHistory(): Promise<void> {
  const token = getToken();
  await fetch(`${BASE_URL}/api/v1/coach/history`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

// ── Streaming chat ────────────────────────────────────────────────────────────

/**
 * Send a message to the coach and stream the reply via SSE.
 *
 * Calls `onDelta` for each text chunk (for streaming UI).
 * Calls `onEvent` for action events (food_logged, workout_logged, etc.)
 * Calls `onDone` when the stream completes.
 * Calls `onError` on network or parse errors.
 */
export async function sendCoachMessage(
  message: string,
  callbacks: {
    onDelta: (chunk: string) => void;
    onEvent: (event: CoachSSEEvent) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  }
): Promise<void> {
  const token = getToken();

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/v1/coach/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message }),
    });
  } catch {
    callbacks.onError("Network error — check your connection.");
    return;
  }

  if (!response.ok) {
    callbacks.onError(`Server error (${response.status}). Try again.`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response stream available.");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE lines: each event is "data: <json>\n\n"
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? ""; // keep incomplete last line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;

        const jsonStr = trimmed.slice(5).trim();
        if (!jsonStr) continue;

        let event: CoachSSEEvent;
        try {
          event = JSON.parse(jsonStr) as CoachSSEEvent;
        } catch {
          continue; // skip malformed lines
        }

        if (event.type === "text_delta") {
          callbacks.onDelta(event.content);
        } else if (event.type === "done") {
          callbacks.onDone();
        } else if (event.type === "error") {
          callbacks.onError(event.message);
        } else {
          // food_logged, workout_logged, steps_logged
          callbacks.onEvent(event);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
