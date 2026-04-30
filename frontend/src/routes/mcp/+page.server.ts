import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

async function fetchJson(url: string): Promise<unknown> {
	const res = await fetch(url, { headers: { Accept: 'application/json' } });
	if (!res.ok) {
		const text = await res.text();
		throw new Error(`HTTP ${res.status}: ${text.slice(0, 500)}`);
	}
	return res.json() as Promise<unknown>;
}

export const load: PageServerLoad = async () => {
	const base = env.MERIDIAN_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000';

	try {
		const [tools, resources, prompts, templates] = await Promise.all([
			fetchJson(`${base}/api/mcp/tools`),
			fetchJson(`${base}/api/mcp/resources`),
			fetchJson(`${base}/api/mcp/prompts`),
			fetchJson(`${base}/api/mcp/resource-templates`)
		]);

		return {
			baseUrl: base,
			tools,
			resources,
			prompts,
			templates
		};
	} catch (e) {
		const message = e instanceof Error ? e.message : 'Unknown error';
		throw error(502, { message });
	}
};
