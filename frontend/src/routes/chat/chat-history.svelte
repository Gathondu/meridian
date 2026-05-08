<script lang="ts">
	import { tick } from 'svelte';
	import type { ChatSession } from './chat.functions';
	import { getChatsByUserSession, renameChat } from './chat.functions';

	type Props = {
		baseUrl: string;
		userSessionId: string;
		activeSessionId: string;
		refreshKey: number;
		onNewChat: () => void;
		onSelectChat: (sessionId: string) => void;
	};

	let {
		baseUrl,
		userSessionId,
		activeSessionId,
		refreshKey,
		onNewChat,
		onSelectChat
	}: Props = $props();

	let chats: ChatSession[] = $state([]);
	let loading = $state(false);
	let error = $state('');
	let isOpen = $state(true);
	let renamingSessionId = $state<string | null>(null);
	let draftTitle = $state('');

	$effect(() => {
		refreshKey;
		if (userSessionId) {
			void loadChats();
		}
	});

	async function loadChats() {
		loading = true;
		error = '';
		try {
			const response = await getChatsByUserSession(baseUrl, userSessionId);
			chats = response.chats;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load chats';
		} finally {
			loading = false;
		}
	}

	function fallbackTitle(chat: ChatSession) {
		const meaningful = chat.messages.find((message) => {
			const content = message.content.replace(/\s+/g, ' ').trim();
			return (
				message.role === 'user' &&
				content.length > 2 &&
				!/^(hi|hello|hey|yo|thanks|thank you)$/i.test(content) &&
				!/^[^\s@]+@[^\s@]+\.[^\s@]+\s+\d{4,}$/.test(content)
			);
		});
		if (meaningful?.content.trim()) {
			return meaningful.content.trim().slice(0, 58);
		}
		return 'New chat';
	}

	function displayTitle(chat: ChatSession) {
		const title = chat.title?.trim();
		if (
			title &&
			!/^(hi|hello|hey|yo|thanks|thank you)$/i.test(title) &&
			!/^Signed in as /i.test(title)
		) {
			return title;
		}
		return fallbackTitle(chat);
	}

	function formatChatDate(value: string) {
		return new Date(value).toLocaleString([], {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function toggleHistory() {
		isOpen = !isOpen;
	}

	function selectChat(sessionId: string) {
		onSelectChat(sessionId);
		if (window.innerWidth <= 760) {
			isOpen = false;
		}
	}

	async function startRename(event: Event, chat: ChatSession) {
		event.stopPropagation();
		renamingSessionId = chat.session_id;
		draftTitle = displayTitle(chat);
		await tick();
		document.getElementById(`rename-${chat.session_id}`)?.focus();
	}

	function cancelRename(event?: Event) {
		event?.stopPropagation();
		renamingSessionId = null;
		draftTitle = '';
	}

	async function saveRename(event: Event, chat: ChatSession) {
		event.preventDefault();
		event.stopPropagation();
		const title = draftTitle.trim();
		if (!title) return;

		try {
			await renameChat(baseUrl, chat.session_id, title);
			chats = chats.map((item) => (item.session_id === chat.session_id ? { ...item, title } : item));
			cancelRename();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to rename chat';
		}
	}

	function handleRenameKeydown(event: KeyboardEvent, chat: ChatSession) {
		if (event.key === 'Escape') {
			cancelRename(event);
		}
		if (event.key === 'Enter') {
			void saveRename(event, chat);
		}
	}

	function handleChatKeydown(event: KeyboardEvent, sessionId: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			selectChat(sessionId);
		}
	}
</script>

<aside class={`${isOpen ? 'history historyOpen' : 'history'}`} aria-label="Chat history">
	<div class="historyBar">
		<button
			class="toggleButton"
			type="button"
			aria-expanded={isOpen}
			aria-controls="chat-history-panel"
			title={isOpen ? 'Collapse history' : 'Open history'}
			onclick={toggleHistory}
		>
			<span aria-hidden="true">{isOpen ? '<' : '>'}</span>
			<span class="toggleText">History</span>
		</button>
	</div>

	<div id="chat-history-panel" class="panel" aria-hidden={!isOpen}>
		<div class="panelHeader">
			<div>
				<h2>Recent chats</h2>
				<p>{chats.length} saved</p>
			</div>
			<button class="newButton" type="button" onclick={onNewChat}>New</button>
		</div>

		{#if error}
			<p class="error" role="alert">{error}</p>
		{/if}

		{#if loading}
			<p class="stateText">Loading chats...</p>
		{:else if chats.length === 0}
			<div class="emptyState">
				<p>No recent chats yet.</p>
				<span>Your saved conversations will appear here.</span>
			</div>
		{:else}
			<ul class="chatList">
				{#each chats as chat (chat.session_id)}
					<li>
						<div
							class={`${chat.session_id === activeSessionId ? 'chatItem activeChat' : 'chatItem'}`}
							role="button"
							tabindex="0"
							onclick={() => selectChat(chat.session_id)}
							onkeydown={(event) => handleChatKeydown(event, chat.session_id)}
						>
							{#if renamingSessionId === chat.session_id}
								<form class="renameForm" onsubmit={(event) => saveRename(event, chat)}>
									<input
										id={`rename-${chat.session_id}`}
										class="renameInput"
										bind:value={draftTitle}
										placeholder="Chat title"
										aria-label="Chat title"
										onkeydown={(event) => handleRenameKeydown(event, chat)}
										onclick={(event) => event.stopPropagation()}
									/>
									<div class="renameActions">
										<button class="smallButton saveButton" type="submit">Save</button>
										<button class="smallButton" type="button" onclick={cancelRename}>Cancel</button>
									</div>
								</form>
							{:else}
								<span class="chatText">
									<strong>{displayTitle(chat)}</strong>
									<time datetime={chat.created_at}>{formatChatDate(chat.created_at)}</time>
								</span>
								<span
									class="renameButton"
									role="button"
									tabindex="0"
									aria-label="Rename chat"
									title="Rename chat"
									onclick={(event) => startRename(event, chat)}
									onkeydown={(event) => {
										if (event.key === 'Enter' || event.key === ' ') {
											void startRename(event, chat);
										}
									}}
								>
									Edit
								</span>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</aside>

<style>
	.history {
		position: relative;
		z-index: 4;
		display: flex;
		flex: 0 0 3.25rem;
		width: 3.25rem;
		min-width: 3.25rem;
		height: 100vh;
		height: 100dvh;
		overflow: hidden;
		background: #073b34;
		color: #fff;
		box-shadow: 1px 0 14px rgba(15, 23, 42, 0.14);
		transition:
			width 0.22s ease,
			flex-basis 0.22s ease,
			min-width 0.22s ease;
	}

	.historyOpen {
		flex-basis: 19rem;
		width: 19rem;
		min-width: 19rem;
	}

	.historyBar {
		flex: 0 0 3.25rem;
		display: flex;
		justify-content: center;
		padding-top: 0.75rem;
		background: #062f2a;
	}

	.toggleButton {
		width: 2.35rem;
		height: 2.35rem;
		display: grid;
		place-items: center;
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.08);
		color: #fff;
		font: inherit;
		font-weight: 800;
		cursor: pointer;
	}

	.toggleButton:hover {
		background: rgba(255, 255, 255, 0.16);
	}

	.toggleButton:focus-visible,
	.newButton:focus-visible,
	.chatItem:focus-visible,
	.renameButton:focus-visible,
	.smallButton:focus-visible,
	.renameInput:focus-visible {
		outline: 2px solid rgba(37, 211, 102, 0.62);
		outline-offset: 2px;
	}

	.toggleText {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	.panel {
		flex: 1 1 auto;
		width: 15.75rem;
		min-width: 15.75rem;
		box-sizing: border-box;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: #f7faf8;
		color: #17211b;
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.16s ease;
	}

	.historyOpen .panel {
		opacity: 1;
		pointer-events: auto;
	}

	.panelHeader {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.9rem;
		border-bottom: 1px solid rgba(15, 23, 42, 0.08);
		background: #fff;
	}

	.panelHeader > div {
		min-width: 0;
	}

	.panelHeader h2,
	.panelHeader p {
		margin: 0;
	}

	.panelHeader h2 {
		font-size: 1rem;
		line-height: 1.2;
	}

	.panelHeader p {
		margin-top: 0.15rem;
		color: #64716a;
		font-size: 0.76rem;
	}

	.newButton,
	.smallButton {
		border: 0;
		border-radius: 7px;
		background: #128c7e;
		color: #fff;
		font: inherit;
		font-weight: 800;
		cursor: pointer;
	}

	.newButton {
		min-width: 3.4rem;
		min-height: 2.1rem;
		padding: 0.42rem 0.68rem;
	}

	.newButton:hover,
	.saveButton:hover {
		background: #0f7d70;
	}

	.error,
	.stateText,
	.emptyState {
		margin: 0.85rem;
		font-size: 0.88rem;
		line-height: 1.4;
	}

	.error {
		padding: 0.65rem;
		border: 1px solid #fecaca;
		border-radius: 8px;
		background: #fef2f2;
		color: #991b1b;
	}

	.stateText,
	.emptyState {
		color: #5b665f;
	}

	.emptyState {
		padding: 0.8rem;
		border: 1px dashed rgba(7, 94, 84, 0.2);
		border-radius: 8px;
		background: #fff;
	}

	.emptyState p {
		margin: 0 0 0.2rem;
		color: #17211b;
		font-weight: 800;
	}

	.chatList {
		flex: 1 1 auto;
		min-height: 0;
		margin: 0;
		padding: 0.45rem;
		box-sizing: border-box;
		overflow-y: auto;
		overflow-x: hidden;
		list-style: none;
	}

	.chatList li {
		min-width: 0;
	}

	.chatItem {
		width: 100%;
		box-sizing: border-box;
		min-height: 3.65rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.6rem;
		margin: 0;
		padding: 0.58rem 0.62rem;
		border: 1px solid transparent;
		border-radius: 8px;
		background: transparent;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}

	.chatItem:hover {
		background: #eef8f2;
	}

	.activeChat {
		border-color: rgba(18, 140, 126, 0.26);
		background: #dcf8c6;
	}

	.chatText {
		flex: 1 1 auto;
		min-width: 0;
		display: grid;
		gap: 0.22rem;
	}

	.chatText strong {
		overflow: hidden;
		color: #17211b;
		font-size: 0.9rem;
		line-height: 1.22;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.chatText time {
		color: #66716b;
		font-size: 0.74rem;
		line-height: 1.1;
	}

	.renameButton {
		flex: 0 0 auto;
		padding: 0.25rem 0.4rem;
		border-radius: 6px;
		color: #075e54;
		font-size: 0.75rem;
		font-weight: 800;
		line-height: 1;
	}

	.renameButton:hover {
		background: rgba(18, 140, 126, 0.12);
	}

	.renameForm {
		width: 100%;
		min-width: 0;
		box-sizing: border-box;
		display: grid;
		gap: 0.45rem;
	}

	.renameInput {
		width: 100%;
		box-sizing: border-box;
		padding: 0.48rem 0.55rem;
		border: 1px solid rgba(18, 140, 126, 0.24);
		border-radius: 7px;
		background: #fff;
		color: #17211b;
		font: inherit;
	}

	.renameActions {
		display: flex;
		gap: 0.4rem;
	}

	.smallButton {
		min-height: 1.85rem;
		padding: 0.28rem 0.55rem;
		background: #64716a;
		font-size: 0.78rem;
	}

	.saveButton {
		background: #128c7e;
	}

	@media (max-width: 760px) {
		.history {
			position: fixed;
			left: 0;
			top: 0;
			height: 100dvh;
		}

		.historyOpen {
			width: min(19rem, 88vw);
			min-width: min(19rem, 88vw);
		}
	}
</style>
