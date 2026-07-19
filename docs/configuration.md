# Конфигурация

## Настройки приложения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `APP_DOMAIN` | Домен Caddy | обязательно |
| `MINI_APP_URL` | Полный URL `/app/` | обязательно |
| `BOT_TOKEN` | Токен BotFather | обязательно |
| `ALLOWED_TELEGRAM_IDS` | JSON-массив администраторов | обязательно |
| `AUTH_MAX_AGE_SECONDS` | Максимальный возраст initData | `900` |
| `SERVERS_FILE` | Инвентарь серверов внутри контейнера | `/config/servers.json` |
| `SERVER_PROBE_CONCURRENCY` | Одновременные проверки overview | `10` |
| `BACKUP_RETENTION_DAYS` | Хранение API-бэкапов | `30` |
| `BOT_OUTPUT_MAX_CHARS` | Вывод SSH в Telegram | `12000` |
| `ENABLE_API_DOCS` | Swagger `/api/docs` | `false` |
| `DEV_BYPASS_AUTH` | Локальный bypass Telegram | `false` |

`DEV_BYPASS_AUTH` разрешён только при localhost Mini App URL.

## Поля сервера

| Поле | Описание |
|---|---|
| `id` | Уникальный стабильный ID: `a-z0-9_-` |
| `name` | Отображаемое имя |
| `location` | Локация |
| `ssh_host`, `ssh_port` | SSH endpoint |
| `ssh_user` | Рекомендуется только `xuiadmin` |
| `ssh_key_path` | Путь внутри контейнера |
| `ssh_known_hosts_path` | Обычно `/run/secrets/known_hosts` |
| `panel_url` | URL вместе с секретным web base path |
| `panel_api_token` | Предпочтительная авторизация |
| `panel_username`, `panel_password` | Session login fallback |
| `panel_verify_tls` | Проверка TLS; выключать только для private/tunnel HTTP(S) |
| `public_host` | Fallback адрес для старого генератора ссылок |
| `system_update_command` | Фиксированный wrapper обновления ОС |
| `panel_update_command` | Фиксированный wrapper обновления панели |
| `enable_raw_ssh` | Разрешить `/ssh`; запрещено с `root` |
| `raw_ssh_timeout` | Timeout raw SSH, максимум 600 секунд |

## Ссылки на переменные окружения

В JSON допускается полное строковое значение `${VARIABLE_NAME}`:

```json
"panel_api_token": "${DE_PANEL_TOKEN}"
```

Переменная должна существовать в окружении контейнера. Частичная интерполяция внутри строки не выполняется.

## Старый формат

`SERVERS=[{...}]` в `.env` остаётся совместимым. Одновременное использование `SERVERS` и `SERVERS_FILE` запрещено, чтобы исключить неоднозначность.
