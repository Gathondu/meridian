/** Parse SSE ``data:`` JSON lines from a streamed chat response. */

export type ChatSseEvent = Record<string, unknown>;

export type ChatTranscriptMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
};

export type ChatSession = {
  session_id: string;
  created_at: string;
  /** New fields for user session grouping and chat renaming */
  user_session_id: string | null;
  title: string | null;
  messages: ChatTranscriptMessage[];
};

export type ChatListResponse = {
  chats: ChatSession[];
};

export async function createPendingChatSession(
  baseUrl: string,
): Promise<string> {
  const res = await fetch(`${baseUrl}/api/chat/sessions`, { method: "POST" });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  const body = (await res.json()) as { session_id?: string };
  if (typeof body.session_id !== "string" || !body.session_id) {
    throw new Error("Invalid session response");
  }
  return body.session_id;
}

export async function createChatWithUserSession(
  baseUrl: string,
  userSessionId: string | null,
  title: string | null,
): Promise<string> {
  const res = await fetch(`${baseUrl}/api/chat/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_session_id: userSessionId, title }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  const body = (await res.json()) as { session_id?: string };
  if (typeof body.session_id !== "string" || !body.session_id) {
    throw new Error("Invalid session response");
  }
  return body.session_id;
}

export async function loadChatSession(
  baseUrl: string,
  sessionId: string,
): Promise<ChatSession> {
  const res = await fetch(
    `${baseUrl}/api/chat/sessions/${encodeURIComponent(sessionId)}`,
  );
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  const body = (await res.json()) as ChatSession;
  if (body.session_id !== sessionId || !Array.isArray(body.messages)) {
    throw new Error("Invalid session response");
  }
  return body;
}

export async function getChatsByUserSession(
  baseUrl: string,
  userSessionId: string | null,
): Promise<ChatListResponse> {
  const url = userSessionId
    ? `${baseUrl}/api/chat/chats?user_session_id=${encodeURIComponent(userSessionId)}`
    : `${baseUrl}/api/chat/chats`;
  const res = await fetch(url);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return (await res.json()) as ChatListResponse;
}

export async function renameChat(
  baseUrl: string,
  sessionId: string,
  title: string,
): Promise<void> {
  const res = await fetch(
    `${baseUrl}/api/chat/chats/${encodeURIComponent(sessionId)}/title`,
    {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=UTF-8" },
      body: title,
    },
  );
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
}

export async function consumeChatSse(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: ChatSseEvent) => void,
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const raw of chunks) {
      const block = raw.trim();
      if (!block.startsWith("data:")) continue;
      const payload = block.slice(5).trim();
      if (!payload) continue;
      try {
        onEvent(JSON.parse(payload) as ChatSseEvent);
      } catch {
        // ignore malformed chunk
      }
    }
  }
}
