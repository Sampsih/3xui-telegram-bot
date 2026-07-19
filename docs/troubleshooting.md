# Решение проблем

## `error parsing value for field servers`

Проверьте JSON:

```bash
python3 -m json.tool config/servers.json >/dev/null
make validate
```

В JSON нужна запятая после каждого поля, кроме последнего перед `}`.

## `ssh_known_hosts_path Field required`

Добавьте каждому серверу:

```json
"ssh_known_hosts_path": "/run/secrets/known_hosts"
```

## `Host key verification failed`

Не используйте `StrictHostKeyChecking=no`. Проверьте fingerprint и обновите `secrets/known_hosts`.

## `Permission denied (publickey)`

Проверьте имя пользователя, путь ключа и права:

```bash
chmod 600 secrets/id_ed25519_*
ssh -i secrets/id_ed25519_server1 xuiadmin@SERVER_HOST id
```

## Ошибка sudoers `unknown setting: requiretty`

Актуальный `scripts/xuiadmin.sudoers` не содержит `requiretty`. Повторно скопируйте файл и запустите `install-managed-host`.

## Кнопка обновления ОС отсутствует

Проверьте наличие `system_update_command` в объекте сервера и пересоздайте `api` и `bot`.

## Кнопка обновления 3x-ui отсутствует

Она показывается только если настроен wrapper и доступен более новый стабильный релиз.

## Ссылка содержит `localhost` или имя tunnel-контейнера

Настройте внешний Sub Domain/Sub Port в Subscription Settings самой 3x-ui.

## Mini App возвращает 401

Открывайте её кнопкой бота. Проверьте `BOT_TOKEN`, `MINI_APP_URL`, время на сервере и возраст `initData`.

## `/logs` ничего не показывает

Повторно запустите `install-managed-host`: он добавляет `xuiadmin` в группу `systemd-journal`. Затем создайте новую SSH-сессию.

## Диагностика контейнеров

```bash
docker compose ps
docker compose logs --tail=200 api bot caddy
curl -i https://YOUR_DOMAIN/health
curl -i https://YOUR_DOMAIN/ready
```
