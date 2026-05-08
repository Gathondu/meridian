import { dev } from '$app/environment';
import { PUBLIC_MERIDIAN_API_BASE_URL } from '$env/static/public';
import type { PageLoad } from './$types';

export const prerender = false;

function apiBaseUrl(): string {
	const raw = PUBLIC_MERIDIAN_API_BASE_URL.trim();
	const base = raw.replace(/\/$/, '');
	if (base) return base;
	if (dev) return 'http://127.0.0.1:8000';
	throw new Error('PUBLIC_MERIDIAN_API_BASE_URL is required for production builds.');
}

export const load: PageLoad = async () => {
	return { baseUrl: apiBaseUrl() };
};
