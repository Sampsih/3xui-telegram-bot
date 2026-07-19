# Development

[Russian version](development.md)

## Local environment

Python 3.12+, Node.js for syntax checks, and Docker Compose are required.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
make bootstrap
```

To run without Telegram, use localhost only:

```dotenv
MINI_APP_URL=http://localhost:8000/app/
DEV_BYPASS_AUTH=true
ALLOWED_TELEGRAM_IDS=[1]
```

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

## Checks

```bash
make validate
make test
make syntax
```

## Structure

```text
backend/app/routers/   HTTP endpoints
backend/app/services/  3x-ui, SSH, links, jobs, releases
frontend/              dependency-free Mini App
config/                scalable server inventory
scripts/               host provisioning and update wrappers
docs/                  operations documentation
```

Never add real `.env` files, `config/servers.json`, SSH keys, audit logs, or databases to fixtures or commits.
