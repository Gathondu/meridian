/** Shape MCP inspection payloads for display (no business logic beyond mapping). */

export type ToolRow = {
	name: string;
	description?: string | null;
};

export type ResourceRow = {
	uri: string;
	name?: string | null;
	title?: string | null;
	description?: string | null;
	mimeType?: string | null;
};

export type PromptRow = {
	name: string;
	title?: string | null;
	description?: string | null;
};

export type TemplateRow = {
	uriTemplate: string;
	name?: string | null;
	title?: string | null;
	description?: string | null;
};

export function toolsFromPayload(data: unknown): ToolRow[] {
	if (!data || typeof data !== 'object' || !('tools' in data)) return [];
	const tools = (data as { tools: unknown }).tools;
	if (!Array.isArray(tools)) return [];
	return tools.map((t) => ({
		name: String((t as { name?: unknown }).name ?? ''),
		description: (t as { description?: string | null }).description ?? null
	}));
}

export function resourcesFromPayload(data: unknown): ResourceRow[] {
	if (!data || typeof data !== 'object' || !('resources' in data)) return [];
	const resources = (data as { resources: unknown }).resources;
	if (!Array.isArray(resources)) return [];
	return resources.map((r) => ({
		uri: String((r as { uri?: unknown }).uri ?? ''),
		name: (r as { name?: string | null }).name ?? null,
		title: (r as { title?: string | null }).title ?? null,
		description: (r as { description?: string | null }).description ?? null,
		mimeType: (r as { mimeType?: string | null }).mimeType ?? null
	}));
}

export function promptsFromPayload(data: unknown): PromptRow[] {
	if (!data || typeof data !== 'object' || !('prompts' in data)) return [];
	const prompts = (data as { prompts: unknown }).prompts;
	if (!Array.isArray(prompts)) return [];
	return prompts.map((p) => ({
		name: String((p as { name?: unknown }).name ?? ''),
		title: (p as { title?: string | null }).title ?? null,
		description: (p as { description?: string | null }).description ?? null
	}));
}

export function templatesFromPayload(data: unknown): TemplateRow[] {
	if (!data || typeof data !== 'object') return [];
	const raw = data as { resourceTemplates?: unknown; resource_templates?: unknown };
	const templates = raw.resourceTemplates ?? raw.resource_templates;
	if (!Array.isArray(templates)) return [];
	return templates.map((x) => ({
		uriTemplate: String(
			(x as { uriTemplate?: unknown; uri_template?: unknown }).uriTemplate ??
				(x as { uri_template?: unknown }).uri_template ??
				''
		),
		name: (x as { name?: string | null }).name ?? null,
		title: (x as { title?: string | null }).title ?? null,
		description: (x as { description?: string | null }).description ?? null
	}));
}
