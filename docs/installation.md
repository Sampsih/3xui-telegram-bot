# Установка

## 1. Что понадобится

- отдельный Linux-сервер для приложения;
- Docker Engine и Docker Compose v2;
- домен, направленный на сервер приложения;
- открытые TCP-порты 80 и 443;
- Telegram-бот от BotFather;
- root-доступ для первоначальной подготовки каждого управляемого сервера;
- установленная MHSanaei/3x-ui.

После подготовки приложение не использует root SSH. Для него создаётся отдельный пользователь `xuiadmin`.

## 2. Получение проекта

```bash
git clone https://github.com/Sampsih/3xui-telegram-bot.git
cd 3xui-telegram-bot
make bootstrap
```

Будут созданы:

- `.env` из публичного примера;
- `config/servers.json` из примера инвентаря;
- приватные каталоги `data` и `secrets`.

## 3. Telegram

1. Создайте бота через BotFather.
2. Запишите токен в `BOT_TOKEN`.
3. Добавьте цифровые Telegram ID администраторов в `ALLOWED_TELEGRAM_IDS`.
4. После запуска установите Main Mini App или Menu Button на `https://APP_DOMAIN/app/`.

## 4. SSH-ключи

Создайте отдельный ключ для каждого сервера:

```bash
ssh-keygen -t ed25519 -f secrets/id_ed25519_server1 -C xuiadmin-server1
chmod 600 secrets/id_ed25519_server1
chmod 644 secrets/id_ed25519_server1.pub
```

С управляющего сервера скопируйте installer, wrappers, sudoers и публичный ключ во временный каталог управляемого сервера:

```bash
ssh root@SERVER_HOST 'install -d -m 700 /tmp/xui-managed-host'
scp \
  scripts/install-managed-host \
  scripts/xui-system-update \
  scripts/xui-safe-update \
  scripts/xuiadmin.sudoers \
  secrets/id_ed25519_server1.pub \
  root@SERVER_HOST:/tmp/xui-managed-host/
ssh root@SERVER_HOST \
  'chmod 755 /tmp/xui-managed-host/install-managed-host && \
   /tmp/xui-managed-host/install-managed-host /tmp/xui-managed-host/id_ed25519_server1.pub'
```

Скрипт создаёт `xuiadmin`, устанавливает update wrappers и проверяет sudoers.

Если SSH использует нестандартный порт, добавьте `-p PORT` к `ssh` и `-P PORT` к `scp`.

Проверьте доступ:

```bash
ssh -i secrets/id_ed25519_server1 xuiadmin@SERVER_HOST \
  'id; systemctl is-active x-ui; sudo -n -l'
```

## 5. known_hosts

Никогда не отключайте проверку host key. Сначала сверьте fingerprint сервера через доверенный канал, затем добавьте ключ:

```bash
ssh-keyscan -H -p 22 SERVER_HOST >> secrets/known_hosts
chmod 644 secrets/known_hosts
```

## 6. `.env`

```bash
nano .env
chmod 600 .env
```

Обязательные значения:

```dotenv
APP_DOMAIN=xui-admin.example.com
MINI_APP_URL=https://xui-admin.example.com/app/
BOT_TOKEN=...
ALLOWED_TELEGRAM_IDS=[123456789]
SERVERS_FILE=/config/servers.json
```

Секреты панелей можно задать отдельными переменными и сослаться на них из инвентаря как `${VARIABLE_NAME}`.

## 7. Инвентарь серверов

Откройте `config/servers.json`. Удалите ненужные примеры и заполните объект каждого сервера. Минимальный пример:

```json
[
  {
    "id": "de-1",
    "name": "Germany 1",
    "ssh_host": "203.0.113.10",
    "ssh_port": 22,
    "ssh_user": "xuiadmin",
    "ssh_key_path": "/run/secrets/id_ed25519_server1",
    "ssh_known_hosts_path": "/run/secrets/known_hosts",
    "panel_url": "https://panel.example.com:2053/secret-path",
    "panel_api_token": "${SERVER1_PANEL_API_TOKEN}",
    "panel_verify_tls": true,
    "system_update_command": "sudo -n /usr/local/sbin/xui-system-update",
    "panel_update_command": "sudo -n /usr/local/sbin/xui-safe-update",
    "enable_raw_ssh": false
  }
]
```

```bash
chmod 600 config/servers.json
make validate
```

## 8. Панель только через SSH

Скопируйте overlay:

```bash
cp docker-compose.tunnel.example.yml docker-compose.tunnel.yml
```

Заполните `TUNNEL_*` в `.env` и используйте в инвентаре URL вида:

```text
http://panel-tunnel:28481/secret-path
```

Запуск с overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

Для нескольких закрытых панелей создайте по tunnel-сервису с уникальным именем и локальным портом либо используйте WireGuard/private network.

## 9. Запуск

```bash
docker compose config -q
docker compose build --pull api bot
docker compose up -d
docker compose ps
docker compose logs --tail=150 api bot caddy
```

Проверки:

```bash
curl -fsS https://YOUR_DOMAIN/health
curl -fsS https://YOUR_DOMAIN/ready
```

`/health` проверяет процесс, `/ready` — наличие серверов и доступность каталога данных.

## 10. Настройка ссылок 3x-ui

В Subscription Settings каждой панели задайте внешний Sub Domain и Sub Port. Это обязательно для панелей за SSH-туннелем: 3x-ui должна генерировать публичный адрес, а не `localhost` или имя Docker-сервиса.

## 11. Проверка после запуска

1. Откройте бота и выполните `/servers`.
2. Проверьте `/status SERVER_ID` и `/logs SERVER_ID 30`.
3. Откройте Mini App.
4. Сравните ссылку существующего клиента со ссылкой в 3x-ui.
5. Создайте тестового клиента и проверьте QR.
6. Только после этого проверяйте обновления.
