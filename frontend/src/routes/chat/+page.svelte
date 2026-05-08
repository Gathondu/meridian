<script lang="ts">
	import { onMount, tick } from 'svelte';
	import type { PageData } from './$types';
	import styles from './+page.module.css';
	import ChatHistory from './chat-history.svelte';
	import ChatMarkdown from './chat-markdown.svelte';
	import {
		consumeChatSse,
		createChatWithUserSession,
		loadChatSession,
		renameChat
	} from './chat.functions';

	let { data }: { data: PageData } = $props();

	const sessionStorageKey = 'meridian.chat.sessionId';
	const userSessionStorageKey = 'meridian.chat.userSessionId';

	let sessionId = $state('');
	let userSessionId = $state('');
	let message = $state('');
	type ToolStatus = {
		name: string;
		state: 'running' | 'done' | 'failed';
		detail?: string;
	};
	type ChatMessage = {
		id: number;
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
	};
	type SelectedItem = {
		sku: string;
		quantity: number;
	};
	let messages: ChatMessage[] = $state([]);
	let selectedItems: SelectedItem[] = $state([]);
	let streaming = $state('');
	let toolStatus: ToolStatus | null = $state(null);
	let err = $state('');
	let busy = $state(false);
	let restoring = $state(false);
	let messageId = $state(0);
	let historyRefreshKey = $state(0);
	let currentTitle = $state<string | null>(null);
	let messagesPane: HTMLDivElement | undefined;

	async function scrollToLatest() {
		await tick();
		messagesPane?.scrollTo({
			top: messagesPane.scrollHeight,
			behavior: 'smooth'
		});
	}

	function formatToolName(name: string) {
		return name.replace(/[_-]+/g, ' ');
	}

	function addSelectedItem(sku: string) {
		const existing = selectedItems.find((item) => item.sku === sku);
		if (existing) {
			selectedItems = selectedItems.map((item) =>
				item.sku === sku ? { ...item, quantity: item.quantity + 1 } : item
			);
		} else {
			selectedItems = [...selectedItems, { sku, quantity: 1 }];
		}
	}

	function changeSelectedQuantity(sku: string, delta: number) {
		selectedItems = selectedItems
			.map((item) =>
				item.sku === sku ? { ...item, quantity: Math.max(0, item.quantity + delta) } : item
			)
			.filter((item) => item.quantity > 0);
	}

	function removeSelectedItem(sku: string) {
		selectedItems = selectedItems.filter((item) => item.sku !== sku);
	}

	function selectedItemsText() {
		return selectedItems.map((item) => `- ${item.sku} x${item.quantity}`).join('\n');
	}

	function createBrowserSessionId() {
		if (crypto.randomUUID) {
			return crypto.randomUUID();
		}
		return `browser-${Date.now()}-${Math.random().toString(16).slice(2)}`;
	}

	function ensureUserSessionId() {
		const saved = localStorage.getItem(userSessionStorageKey);
		if (saved) {
			userSessionId = saved;
			return saved;
		}
		const created = createBrowserSessionId();
		localStorage.setItem(userSessionStorageKey, created);
		userSessionId = created;
		return created;
	}

	function titleFromMessage(text: string) {
		const title = text.replace(/\s+/g, ' ').trim();
		if (!title || /^(hi|hello|hey|yo|thanks|thank you)$/i.test(title)) {
			return null;
		}
		if (/^[^\s@]+@[^\s@]+\.[^\s@]+\s+\d{4,}$/.test(title)) {
			const email = title.split(/\s+/)[0];
			return `Signed in as ${email}`;
		}
		return title.length > 58 ? `${title.slice(0, 55)}...` : title;
	}

	function draftOrderMessage() {
		if (selectedItems.length === 0) return;
		message = `Place the order for:\n${selectedItemsText()}`;
	}

	async function placeSelectedOrder() {
		if (selectedItems.length === 0 || busy || restoring) return;
		message = `Place the order for:\n${selectedItemsText()}`;
		await tick();
		await submitMessage();
		selectedItems = [];
	}

	function rememberSession(id: string) {
		localStorage.setItem(sessionStorageKey, id);
	}

	function clearSession() {
		localStorage.removeItem(sessionStorageKey);
		sessionId = '';
		message = '';
		messages = [];
		selectedItems = [];
		streaming = '';
		toolStatus = null;
		err = '';
		messageId = 0;
		currentTitle = null;
	}

	function startNewChat() {
		clearSession();
		historyRefreshKey += 1;
	}

	async function restoreSession(id: string) {
		restoring = true;
		err = '';
		try {
			const session = await loadChatSession(data.baseUrl, id);
			sessionId = session.session_id;
			currentTitle = session.title;
			rememberSession(session.session_id);
			messageId = 0;
			messages = session.messages.map((row) => ({
				id: messageId++,
				role: row.role,
				content: row.content,
				timestamp: row.timestamp || session.created_at
			}));
			await scrollToLatest();
		} catch {
			clearSession();
		} finally {
			restoring = false;
		}
	}

	async function submitMessage(textOverride?: string) {
		const text = (textOverride ?? message).trim();
		if (!text) return;
		err = '';
		streaming = '';
		toolStatus = null;

		// Add user message
		const userMessage = {
			id: messageId++,
			role: 'user' as const,
			content: text,
			timestamp: new Date().toISOString()
		};
		messages = [...messages, userMessage];
		scrollToLatest();

		if (!textOverride) {
			message = '';
		}
		busy = true;

		try {
			if (!sessionId) {
				const currentUserSessionId = userSessionId || ensureUserSessionId();
				sessionId = await createChatWithUserSession(
					data.baseUrl,
					currentUserSessionId,
					titleFromMessage(text)
				);
				currentTitle = titleFromMessage(text);
				rememberSession(sessionId);
				historyRefreshKey += 1;
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
					if (toolStatus?.state !== 'running') {
						toolStatus = null;
					}
					assistant += ev.text;
					streaming = assistant;
					scrollToLatest();
				}
				if (ev.type === 'tool_call_start' && typeof ev.name === 'string') {
					toolStatus = {
						name: ev.name,
						state: 'running'
					};
					scrollToLatest();
				}
				if (ev.type === 'tool_call_done') {
					const ok = ev.ok === true;
					const name = typeof ev.name === 'string' ? ev.name : 'tool';
					toolStatus = {
						name,
						state: ok ? 'done' : 'failed',
						detail: !ok && typeof ev.text === 'string' ? ev.text : undefined
					};
					scrollToLatest();
				}
				if (ev.type === 'error' && typeof ev.message === 'string') {
					err = ev.message;
				}
			});
			// Add assistant message
			if (assistant.trim()) {
				const assistantMessage = {
					id: messageId++,
					role: 'assistant' as const,
					content: assistant,
					timestamp: new Date().toISOString()
				};
				messages = [...messages, assistantMessage];
			}
			streaming = '';
			toolStatus = null;
			const nextTitle = titleFromMessage(text);
			if (sessionId && nextTitle && (!currentTitle || currentTitle === 'New chat')) {
				try {
					await renameChat(data.baseUrl, sessionId, nextTitle);
					currentTitle = nextTitle;
				} catch {
					// The chat itself succeeded; title updates are best-effort.
				}
			}
			historyRefreshKey += 1;
			scrollToLatest();
		} catch (e) {
			err = e instanceof Error ? e.message : 'Stream failed';
			streaming = '';
			toolStatus = null;
		} finally {
			busy = false;
		}
	}

	function sendMessage(e: SubmitEvent) {
		e.preventDefault();
		void submitMessage();
	}

	function viewOrderLineItems(orderId: string) {
		if (busy || restoring) return;
		void submitMessage(`Show me the line items for order ${orderId}.`);
	}

	function viewCustomerProfile(customerId: string) {
		if (busy || restoring) return;
		void submitMessage(`Show me the customer profile for customer ${customerId}.`);
	}

	function handleComposerKeydown(e: KeyboardEvent) {
		if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
		e.preventDefault();
		if (!busy && !restoring && message.trim()) {
			void submitMessage();
		}
	}

	onMount(() => {
		ensureUserSessionId();
		const savedSessionId = localStorage.getItem(sessionStorageKey);
		if (savedSessionId) {
			void restoreSession(savedSessionId);
		}
	});
</script>

<div class={styles.pageShell}>
	<ChatHistory
		baseUrl={data.baseUrl}
		{userSessionId}
		activeSessionId={sessionId}
		refreshKey={historyRefreshKey}
		onNewChat={startNewChat}
		onSelectChat={(id) => void restoreSession(id)}
	/>

<main class={styles.main}>
	<header class={styles.header}>
		<div class={styles.identity}>
			<div class={styles.avatar} aria-hidden="true">M</div>
			<div>
				<h1 class={styles.title}>Meridian</h1>
				<p class={styles.meta}>Order help and secure verification in chat</p>
			</div>
		</div>
		<div class={styles.headerActions}>
			{#if sessionId || messages.length > 0}
				<button class={styles.headerButton} type="button" onclick={startNewChat}>New chat</button>
			{/if}
			<a class={styles.homeLink} href="/">Home</a>
		</div>
	</header>

	{#if err}
		<p class={styles.error} role="alert">{err}</p>
	{/if}

	<div class={styles.messages} bind:this={messagesPane} aria-live="polite">
		{#if messages.length === 0 && !streaming}
			<div class={styles.emptyState}>
				<p class={styles.emptyTitle}>{restoring ? 'Loading conversation' : 'Start a conversation'}</p>
				<p class={styles.emptyText}>
					Meridian will ask for your order email and PIN here when it needs them.
				</p>
			</div>
		{/if}
		{#each messages as message (message.id)}
			<div
				class={`${styles.messageWrapper} ${
					message.role === 'user' ? styles.messageWrapperUser : styles.messageWrapperAssistant
				}`}
			>
				{#if message.role === 'assistant'}
					<div class={`${styles.messageAvatar} ${styles.messageAvatarAssistant}`}>M</div>
				{/if}
				<div
					class={`${styles.messageBubble} ${
						message.role === 'user' ? styles.messageBubbleUser : styles.messageBubbleAssistant
					}`}
				>
					<div class={styles.messageContent}>
						<ChatMarkdown
							content={message.content}
							onSkuClick={addSelectedItem}
							onOrderClick={viewOrderLineItems}
							onCustomerClick={viewCustomerProfile}
						/>
					</div>
					<div class={styles.messageMeta}>
						<span>
							{new Date(message.timestamp).toLocaleTimeString([], {
								hour: '2-digit',
								minute: '2-digit'
							})}
						</span>
					</div>
				</div>
				{#if message.role === 'user'}
					<div class={`${styles.messageAvatar} ${styles.messageAvatarUser}`}>You</div>
				{/if}
			</div>
		{/each}

		{#if streaming}
			<div class={`${styles.messageWrapper} ${styles.messageWrapperAssistant}`}>
				<div class={`${styles.messageAvatar} ${styles.messageAvatarAssistant}`}>M</div>
				<div class={`${styles.messageBubble} ${styles.messageBubbleAssistant}`}>
					<div class={styles.messageContent}>
						<ChatMarkdown
							content={streaming}
							onSkuClick={addSelectedItem}
							onOrderClick={viewOrderLineItems}
							onCustomerClick={viewCustomerProfile}
						/>
					</div>
					<div class={styles.messageMeta}>
						<span>now</span>
					</div>
				</div>
			</div>
		{/if}

		{#if toolStatus}
			<div class={`${styles.messageWrapper} ${styles.messageWrapperAssistant}`}>
				<div class={`${styles.messageAvatar} ${styles.messageAvatarAssistant}`}>M</div>
				<div
					class={`${styles.toolStatus} ${
						toolStatus.state === 'failed' ? styles.toolStatusFailed : ''
					}`}
				>
					<span class={styles.typingDots} aria-hidden="true">
						<span></span>
						<span></span>
						<span></span>
					</span>
					<span>
						{#if toolStatus.state === 'running'}
							{formatToolName(toolStatus.name)}
						{:else if toolStatus.state === 'done'}
							{formatToolName(toolStatus.name)} complete
						{:else}
							{formatToolName(toolStatus.name)} failed
						{/if}
					</span>
				</div>
			</div>
		{:else if busy && !streaming}
			<div class={`${styles.messageWrapper} ${styles.messageWrapperAssistant}`}>
				<div class={`${styles.messageAvatar} ${styles.messageAvatarAssistant}`}>M</div>
				<div class={`${styles.messageBubble} ${styles.messageBubbleAssistant}`}>
					<span class={styles.typingDots} aria-label="Meridian is typing">
						<span></span>
						<span></span>
						<span></span>
					</span>
				</div>
			</div>
		{/if}
	</div>

	<section class={styles.section} aria-labelledby="msg-label">
		<form class={styles.form} onsubmit={sendMessage}>
			{#if selectedItems.length > 0}
				<div class={styles.selectionTray} aria-label="Selected order items">
					<div class={styles.selectionItems}>
						{#each selectedItems as item (item.sku)}
							<div class={styles.selectionItem}>
								<button
									class={styles.selectionSku}
									type="button"
									title={`Use ${item.sku} in the message`}
									onclick={draftOrderMessage}
								>
									{item.sku}
								</button>
								<div class={styles.quantityControls} aria-label={`${item.sku} quantity`}>
									<button type="button" onclick={() => changeSelectedQuantity(item.sku, -1)}>-</button>
									<span>{item.quantity}</span>
									<button type="button" onclick={() => changeSelectedQuantity(item.sku, 1)}>+</button>
								</div>
								<button
									class={styles.removeSelection}
									type="button"
									aria-label={`Remove ${item.sku}`}
									onclick={() => removeSelectedItem(item.sku)}
								>
									x
								</button>
							</div>
						{/each}
					</div>
					<button
						class={styles.placeOrderButton}
						type="button"
						disabled={busy || restoring}
						onclick={placeSelectedOrder}
					>
						Place order
					</button>
				</div>
			{/if}
			<textarea
				id="msg"
				class={styles.input}
				rows="1"
				bind:value={message}
				disabled={busy || restoring}
				placeholder="Type your message…"
				aria-labelledby="msg-label"
				onkeydown={handleComposerKeydown}
			></textarea>
			<label class={styles.label} for="msg" id="msg-label">Message</label>
			<button class={styles.buttonPrimary} type="submit" disabled={busy || restoring || !message.trim()}>
				Send message
			</button>
		</form>
	</section>
</main>
</div>
