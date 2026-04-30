import type { PageLoad } from './$types';

export const prerender = false;

function apiBaseUrl(): string {
	const raw =
		typeof import.meta.env.PUBLIC_MERIDIAN_API_BASE_URL === 'string'
			? import.meta.env.PUBLIC_MERIDIAN_API_BASE_URL.trim()
			: '';
	const base = raw.replace(/\/$/, '');
	return base || 'http://127.0.0.1:8000';
}

export const load: PageLoad = async () => {
	return { baseUrl: apiBaseUrl() };
};
