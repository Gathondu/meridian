# Agent instructions (Meridian)

This repository is a monorepo:

- `frontend/` — SvelteKit (Svelte 5)
- `backend/` — FastAPI (Python, managed with **uv**)
- `infra/terraform/` — AWS infrastructure as code
- `docker/` — container images for deployment

## Cursor context (always use when relevant)

When working in this repo, **attach and follow** these Cursor rules / contexts so behavior stays consistent with project standards:

- `@MCP` — Model Context Protocol usage and available MCP tools where applicable
- `@GoFastMCP` — FastMCP patterns and constraints
- `@FastAPI` — API design, schemas, services layer, dependency injection
- `@Svelte` — Svelte 5 runes, SvelteKit structure, CSS modules, data loading patterns

This file is intentionally minimal and will be **extended over time** as team conventions and automation solidify. Prefer updating `AGENTS.md` instead of scattering one-off instructions across chats.
