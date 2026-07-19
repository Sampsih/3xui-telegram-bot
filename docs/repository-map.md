# Карта репозитория

| Путь | Назначение |
|---|---|
| `backend/app/main.py` | FastAPI, middleware, health/readiness и Mini App |
| `backend/app/bot.py` | Telegram-команды и polling |
| `backend/app/config.py` | Валидация приложения и инвентаря серверов |
| `backend/app/routers/` | HTTP API серверов и клиентов |
| `backend/app/services/xui.py` | Адаптер API 3x-ui |
| `backend/app/services/ssh.py` | SSH и фиксированные операции |
| `backend/app/services/jobs.py` | Фоновые задания и их хранение |
| `frontend/` | Telegram Mini App без отдельного build step |
| `config/servers.example.json` | Безопасный пример масштабируемого инвентаря |
| `scripts/install-managed-host` | Первичная настройка пользователя `xuiadmin` |
| `scripts/xui-*-update` | Root-owned wrappers обновлений |
| `docker-compose.yml` | Основной production stack |
| `docker-compose.tunnel.example.yml` | Опциональный SSH tunnel overlay |
| `docs/` | Эксплуатационная и developer-документация |
| `.github/` | CI, Dependabot и шаблоны GitHub |

Runtime-файлы `.env`, `config/servers.json`, `data/` и ключи в `secrets/` не должны попадать в Git.
