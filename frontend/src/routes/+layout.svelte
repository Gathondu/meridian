<script lang="ts">
	import type { Snippet } from 'svelte';
	import styles from './+layout.module.css';

	let { children }: { children: Snippet } = $props();
</script>

<div class={styles.root}>
	{@render children()}
</div>
