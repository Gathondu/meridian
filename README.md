# Meridian

Monorepo with a SvelteKit frontend, FastAPI backend, Terraform for AWS, and Docker images for deployment.

## Layout

| Path | Purpose |
|------|---------|
| `frontend/` | SvelteKit app (Svelte 5) |
| `backend/` | FastAPI HTTP API |
| `infra/terraform/` | AWS infrastructure (Terraform) |
| `docker/` | Dockerfiles for building images used with Terraform / ECS |

## Prerequisites

- **Node.js** (LTS) and npm
- **uv** for Python environments and dependencies (do not use `pip` for this project)
- **Terraform** (for infrastructure work)
- **Docker** (optional; for building images or local compose)

## Local development

### Backend

```bash
cd backend
uv venv
uv sync
uv run uvicorn meridian_api.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/health`

Read-only MCP inspection (proxied to the configured MCP server via FastMCP):

- `GET /api/mcp/tools`
- `GET /api/mcp/resources`
- `GET /api/mcp/resource-templates`
- `GET /api/mcp/prompts`
- `GET /api/mcp/resources/read?uri=…`

Defaults and env vars are described in [`backend/.env.example`](./backend/.env.example). Tool execution is not exposed over HTTP in this phase; a future chat API will call tools on the server only.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Dev server defaults to `http://127.0.0.1:5173`.

Copy [`frontend/.env.example`](./frontend/.env.example) to `frontend/.env` and set **`MERIDIAN_API_BASE_URL`** (server-only) to your API origin, for example `http://127.0.0.1:8000`, so the `/mcp` inspection page can reach the backend during `npm run dev`.

The UI is served independently during development. For production-style hosting on AWS, use the Dockerfiles under `docker/` and the Terraform layout under `infra/terraform/`.

### Optional: Docker Compose

From the repository root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Adjust ports in `docker/docker-compose.yml` if they conflict with local services.

## Deployment (AWS)

- Define and apply infrastructure in `infra/terraform/` (VPC, ECS/Fargate, ALB, ECR, etc., as you add modules).
- Build and push images using `docker/Dockerfile.backend` and `docker/Dockerfile.frontend` with your registry and CI/CD pipeline.

Details are added as the infrastructure code grows; see `infra/terraform/README.md`.

## Agent guidance

See [AGENTS.md](./AGENTS.md) for how AI assistants should use Cursor rules and MCP context in this repo.
