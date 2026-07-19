## Что изменено / What changed

Кратко опишите изменение и его причину.

Briefly describe the change and why it is needed.

## Как проверено / How it was tested

- [ ] `make validate`
- [ ] `make test`
- [ ] `make syntax`
- [ ] `docker compose config -q`

## Безопасность и совместимость / Security and compatibility

- [ ] В diff нет токенов, паролей, приватных ключей, реальных `servers.json` и `.env`.
- [ ] The diff contains no tokens, passwords, private keys, real `servers.json`, or `.env` files.
- [ ] Изменение не ослабляет проверку Telegram, TLS или SSH host keys.
- [ ] The change does not weaken Telegram, TLS, or SSH host-key verification.
- [ ] Изменение конфигурации отражено в `.env.example`, `config/servers.example.json` и документации.
- [ ] Configuration changes are reflected in `.env.example`, `config/servers.example.json`, and the documentation.
