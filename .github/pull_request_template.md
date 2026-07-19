## Что изменено

Кратко опишите изменение и его причину.

## Как проверено

- [ ] `make validate`
- [ ] `make test`
- [ ] `make syntax`
- [ ] `docker compose config -q`

## Безопасность и совместимость

- [ ] В diff нет токенов, паролей, приватных ключей, реальных `servers.json` и `.env`.
- [ ] Изменение не ослабляет проверку Telegram, TLS или SSH host keys.
- [ ] Изменение конфигурации отражено в `.env.example`, `config/servers.example.json` и документации.
