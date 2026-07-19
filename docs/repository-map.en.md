# Repository map

[Russian version](repository-map.md)

| Path | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI, middleware, health/readiness, and Mini App |
| `backend/app/bot.py` | Telegram commands and polling |
| `backend/app/config.py` | Application and server-inventory validation |
| `backend/app/routers/` | Server and client HTTP API |
| `backend/app/services/xui.py` | 3x-ui API adapter |
| `backend/app/services/ssh.py` | SSH and fixed operations |
| `backend/app/services/jobs.py` | Background jobs and their storage |
| `frontend/` | Telegram Mini App without a separate build step |
| `config/servers.example.json` | Safe example of a scalable inventory |
| `scripts/install-managed-host` | Initial `xuiadmin` user provisioning |
| `scripts/xui-*-update` | Root-owned update wrappers |
| `scripts/validate-docs.py` | Russian/English documentation parity validation |
| `docker-compose.yml` | Main production stack |
| `docker-compose.tunnel.example.yml` | Optional SSH-tunnel overlay |
| `docs/` | Operations and developer documentation |
| `.github/` | CI, Dependabot, and GitHub templates |

Runtime files `.env`, `config/servers.json`, `data/`, and keys in `secrets/` must never be committed to Git.
