<script lang="ts">
	import styles from './+page.module.css';

	const features = [
		{
			href: '/chat',
			kicker: 'Chat',
			title: 'Talk with Meridian',
			description:
				'Start the customer support chat, verify order details in conversation, and stream assistant responses live.',
			action: 'Open chat',
			mark: 'C'
		},
		{
			href: '/mcp',
			kicker: 'MCP tools',
			title: 'List backend MCP tools',
			description:
				'Inspect the backend MCP catalog, including available tools, resources, templates, and prompts.',
			action: 'View tools',
			mark: 'M'
		}
	];
</script>

<main class={styles.main}>
	<section class={styles.hero} aria-labelledby="home-title">
		<p class={styles.eyebrow}>Meridian workspace</p>
		<h1 id="home-title" class={styles.title}>Choose a workflow</h1>
		<p class={styles.lead}>
			Jump into the support chat or inspect the MCP capabilities exposed by the backend.
		</p>
	</section>

	<section class={styles.cards} aria-label="Meridian features">
		{#each features as feature (feature.href)}
			<a class={styles.card} href={feature.href}>
				<span class={styles.cardMark} aria-hidden="true">{feature.mark}</span>
				<span class={styles.cardBody}>
					<span class={styles.kicker}>{feature.kicker}</span>
					<span class={styles.cardTitle}>{feature.title}</span>
					<span class={styles.cardDescription}>{feature.description}</span>
					<span class={styles.cardAction}>{feature.action}</span>
				</span>
			</a>
		{/each}
	</section>
</main>
