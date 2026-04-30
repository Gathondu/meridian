<script lang="ts">
	import type { PageData } from './$types';
	import {
		promptsFromPayload,
		resourcesFromPayload,
		templatesFromPayload,
		toolsFromPayload
	} from './mcp.functions';
	import styles from './+page.module.css';

	let { data }: { data: PageData } = $props();

	const toolRows = $derived(toolsFromPayload(data.tools));
	const resourceRows = $derived(resourcesFromPayload(data.resources));
	const promptRows = $derived(promptsFromPayload(data.prompts));
	const templateRows = $derived(templatesFromPayload(data.templates));
</script>

<div class={styles.wrap}>
	<a class={styles.back} href="/">← Home</a>
	<h1 class={styles.title}>MCP inspection</h1>
	<p class={styles.meta}>Backend: <span class={styles.mono}>{data.baseUrl}</span> (read-only catalog)</p>

	<section class={styles.section} aria-labelledby="tools-h">
		<h2 id="tools-h" class={styles.sectionTitle}>Tools</h2>
		<table class="{styles.table} {styles.toolsTable}">
			<thead>
				<tr>
					<th class="{styles.th} {styles.toolNameTh}">Name</th>
					<th class={styles.th}>Description</th>
				</tr>
			</thead>
			<tbody>
				{#each toolRows as row (row.name)}
					<tr>
						<td class="{styles.td} {styles.toolNameTd}">
							<code class="{styles.mono} {styles.toolNameCode}" title={row.name}>{row.name}</code>
						</td>
						<td class={styles.td}>{row.description ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section class={styles.section} aria-labelledby="res-h">
		<h2 id="res-h" class={styles.sectionTitle}>Resources</h2>
		<table class={styles.table}>
			<thead>
				<tr>
					<th class={styles.th}>URI</th>
					<th class={styles.th}>Name</th>
					<th class={styles.th}>MIME</th>
				</tr>
			</thead>
			<tbody>
				{#each resourceRows as row (row.uri)}
					<tr>
						<td class={styles.td}><code class={styles.mono}>{row.uri}</code></td>
						<td class={styles.td}>{row.name ?? row.title ?? '—'}</td>
						<td class={styles.td}>{row.mimeType ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section class={styles.section} aria-labelledby="tpl-h">
		<h2 id="tpl-h" class={styles.sectionTitle}>Resource templates</h2>
		<table class={styles.table}>
			<thead>
				<tr>
					<th class={styles.th}>URI template</th>
					<th class={styles.th}>Name</th>
				</tr>
			</thead>
			<tbody>
				{#each templateRows as row (row.uriTemplate)}
					<tr>
						<td class={styles.td}><code class={styles.mono}>{row.uriTemplate}</code></td>
						<td class={styles.td}>{row.name ?? row.title ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section class={styles.section} aria-labelledby="prm-h">
		<h2 id="prm-h" class={styles.sectionTitle}>Prompts</h2>
		<table class={styles.table}>
			<thead>
				<tr>
					<th class={styles.th}>Name</th>
					<th class={styles.th}>Description</th>
				</tr>
			</thead>
			<tbody>
				{#each promptRows as row (row.name)}
					<tr>
						<td class={styles.td}><code class={styles.mono}>{row.name}</code></td>
						<td class={styles.td}>{row.description ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>
</div>
