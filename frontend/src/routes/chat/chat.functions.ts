/** Parse SSE ``data:`` JSON lines from a streamed chat response. */

export type ChatSseEvent = Record<string, unknown>;

export async function consumeChatSse(
	reader: ReadableStreamDefaultReader<Uint8Array>,
	onEvent: (event: ChatSseEvent) => void
): Promise<void> {
	const decoder = new TextDecoder();
	let buffer = '';
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		const chunks = buffer.split('\n\n');
		buffer = chunks.pop() ?? '';
		for (const raw of chunks) {
			const block = raw.trim();
			if (!block.startsWith('data:')) continue;
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
