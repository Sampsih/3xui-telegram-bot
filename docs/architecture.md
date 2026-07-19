# Архитектура и масштабирование

## Компоненты

- `bot` — aiogram polling и безопасные SSH-команды;
- `api` — Telegram auth, 3x-ui API, SSH, jobs и аудит;
- `frontend` — статическая Telegram Mini App;
- `caddy` — TLS и reverse proxy;
- `panel-tunnel` — опциональный SSH port forward.

## Добавление серверов

На каждый сервер требуется один объект инвентаря, один SSH-ключ и host key в общем `known_hosts`. Код не содержит фиксированного числа серверов.

Overview использует ограниченный semaphore. Настройте `SERVER_PROBE_CONCURRENCY` в соответствии с размером управляющего сервера и лимитами SSH/panel API.

## Адаптер 3x-ui

Все обращения к панели сосредоточены в `backend/app/services/xui.py`. Для fork с другим API создайте отдельный клиент с тем же набором операций и добавьте новый `panel_type`.

## Операции

Jobs сохраняются в приватных JSON-файлах. Это простая и надёжная схема для одного экземпляра API. Для горизонтального масштабирования замените JobManager на Redis/PostgreSQL и вынесите выполнение в отдельный worker. Remote wrappers уже используют `flock`, поэтому защищают конкретный сервер от параллельных обновлений.

## Сеть

Публичным должен быть только Caddy. API, bot и tunnels находятся в Docker networks без host ports. Панели рекомендуется соединять с управляющим сервером через WireGuard, private network или SSH tunnel.

## Секреты

Текущая Docker-конфигурация использует read-only bind mount `secrets`. Для более крупной установки можно заменить его Docker Secrets, SOPS, Vault или secret manager облачного провайдера без изменения сервисного слоя.
