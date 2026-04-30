<script lang="ts">
	import type { PageData } from './$types';
	import styles from './+page.module.css';
	import { consumeChatSse, createPendingChatSession } from './chat.functions';

	let { data }: { data: PageData } = $props();

	let sessionId = $state('');
	let message = $state('');
	let transcript = $state('');
	let streaming = $state('');
	let err = $state('');
	let busy = $state(false);

	async function sendMessage(e: SubmitEvent) {
		e.preventDefault();
		const text = message.trim();
		if (!text) return;
		err = '';
		streaming = '';
		transcript += (transcript ? '\n\n' : '') + `You: ${text}\n\nAssistant: `;
		message = '';
		busy = true;
		try {
			if (!sessionId) {
				sessionId = await createPendingChatSession(data.baseUrl);
			}
			const res = await fetch(
				`${data.baseUrl}/api/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
					body: JSON.stringify({ text })
				}
			);
			if (!res.ok) {
				const t = await res.text();
				throw new Error(t || res.statusText);
			}
			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');
			let assistant = '';
			await consumeChatSse(reader, (ev) => {
				if (ev.type === 'content_delta' && typeof ev.text === 'string') {
					assistant += ev.text;
					streaming = assistant;
				}
				if (ev.type === 'tool_call_start' && typeof ev.name === 'string') {
					assistant += `\n[calling ${ev.name}…]\n`;
					streaming = assistant;
				}
				if (ev.type === 'tool_call_done') {
					const ok = ev.ok === true;
					const name = typeof ev.name === 'string' ? ev.name : 'tool';
					assistant += ok ? `\n[${name} done]\n` : `\n[${name} failed]\n`;
					if (!ok && typeof ev.text === 'string') {
						assistant += `${ev.text}\n`;
					}
					streaming = assistant;
				}
				if (ev.type === 'error' && typeof ev.message === 'string') {
					err = ev.message;
				}
			});
			transcript += assistant;
			streaming = '';
		} catch (e) {
			err = e instanceof Error ? e.message : 'Stream failed';
			streaming = '';
		} finally {
			busy = false;
		}
	}
</script>

<main class={styles.main}>
	<h1 class={styles.title}>Chat</h1>
	<p class={styles.meta}>
		Send a message to begin. Meridian will ask for your order email and PIN in the conversation—there
		is no separate sign-in form.
	</p>

	<section class={styles.section} aria-labelledby="msg-label">
		<form class={styles.form} onsubmit={sendMessage}>
			<label class={styles.label} for="msg" id="msg-label">Message</label>
			<textarea
				id="msg"
				class={styles.input}
				rows="3"
				bind:value={message}
				disabled={busy}
				placeholder="Type your message…"
			></textarea>
			<p class={styles.actions}>
				<button class={styles.buttonPrimary} type="submit" disabled={busy}>Send</button>
			</p>
		</form>
	</section>

	{#if err}
		<p class={styles.error} role="alert">{err}</p>
	{/if}
	<div class={styles.output} aria-live="polite">{transcript}{streaming}</div>
</main>
