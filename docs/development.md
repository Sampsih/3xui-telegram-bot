# Разработка

## Локальное окружение

Требуются Python 3.12+, Node.js для syntax check и Docker Compose.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
make bootstrap
```

Для запуска без Telegram используйте только localhost:

```dotenv
MINI_APP_URL=http://localhost:8000/app/
DEV_BYPASS_AUTH=true
ALLOWED_TELEGRAM_IDS=[1]
```

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

## Проверки

```bash
make validate
make test
make syntax
```

## Структура

```text
backend/app/routers/   HTTP endpoints
backend/app/services/  3x-ui, SSH, links, jobs, releases
frontend/              dependency-free Mini App
config/                scalable server inventory
scripts/               host provisioning and update wrappers
docs/                  operations documentation
```

Не добавляйте реальные `.env`, `config/servers.json`, SSH-ключи, audit logs или базы в fixtures и commits.
