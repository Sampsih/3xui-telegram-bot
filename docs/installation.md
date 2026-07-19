# Установка

[English version](installation.en.md)

## 1. Что понадобится

- любой Linux-сервер для приложения с Docker Engine и Docker Compose v2;
- Python 3 и OpenSSH client для интерактивной настройки;
- домен, направленный на сервер приложения, и открытые TCP-порты 80/443;
- Telegram-бот от BotFather;
- SSH-доступ к управляемым серверам;
- root или sudo-доступ только для их первоначальной подготовки;
- установленная MHSanaei/3x-ui;
- управляемая Linux ОС с `systemctl`, `rc-service` или `service` и менеджером `apt-get`, `dnf`, `yum`, `zypper`, `apk` либо `pacman`.

После подготовки приложение подключается как отдельный непривилегированный пользователь `xuiadmin`, а не root.

## 2. Получение проекта

```bash
git clone https://github.com/Sampsih/3xui-telegram-bot.git
cd 3xui-telegram-bot
```

## 3. Интерактивная установка

Рекомендуемый способ:

```bash
make install
```

Установщик последовательно запросит:

- язык мастера;
- домен, токен бота и Telegram ID администраторов;
- количество управляемых серверов;
- ID, имя и локацию каждого сервера;
- SSH-адрес и порт;
- публичный адрес для ссылок подключения;
- прямой URL панели или параметры SSH-туннеля;
- API token либо логин и пароль панели;
- необходимость обновления ОС, 3x-ui и raw SSH;
- нужно ли сразу подготовить удалённый сервер и запустить Compose.

Скрипт создаёт приватные `.env`, `config/servers.json`, отдельные ключи в `secrets`, общий `known_hosts` и, при необходимости, `docker-compose.tunnel.yml`. Существующие конфиги перед заменой сохраняются в `data/installer-backups`.

## 4. Проверка host key и подготовка серверов

Для каждого сервера мастер получает host key, показывает fingerprint через `ssh-keygen -lf` и добавляет его только после подтверждения сверки через доверенный канал. Не подтверждайте неизвестный fingerprint.

При согласии мастер копирует `install-managed-host`, `xui-system-update`, `xui-safe-update` и публичный ключ на сервер. Удалённый скрипт создаёт `xuiadmin`, ограниченный sudoers и автоматически определяет пакетный менеджер.

Первичная SSH-авторизация может выполняться как root либо как пользователь с sudo. Пароли и приватные ключи эта операция в проект не копирует.

## 5. Запуск

Если запуск был пропущен в мастере:

```bash
make validate
docker compose config -q
docker compose up -d --build
docker compose ps
```

Проверки:

```bash
curl -fsS https://YOUR_DOMAIN/health
curl -fsS https://YOUR_DOMAIN/ready
```

`/health` проверяет процесс, `/ready` — наличие серверов и доступность каталога данных.

## 6. Telegram

1. Создайте бота через BotFather.
2. Убедитесь, что его токен записан в `BOT_TOKEN`.
3. Убедитесь, что цифровые Telegram ID администраторов находятся в `ALLOWED_TELEGRAM_IDS`.
4. Установите Main Mini App или Menu Button на URL из `MINI_APP_URL`.

## 7. Полностью ручная настройка

Если интерактивный мастер не нужен:

```bash
make bootstrap
```

Будут созданы:

- `.env` из публичного примера;
- `config/servers.json` из примера инвентаря;
- приватные каталоги `data` и `secrets`.

## 8. Ручное создание SSH-ключа

Создайте отдельный ключ для каждого сервера:

```bash
ssh-keygen -t ed25519 -N '' -f secrets/id_ed25519_server1 -C xuiadmin-server1
chmod 600 secrets/id_ed25519_server1
chmod 644 secrets/id_ed25519_server1.pub
```

## 9. Ручная подготовка managed host

Скопируйте installer, wrappers, sudoers и публичный ключ во временный каталог:

```bash
ssh -p 22 root@SERVER_HOST 'install -d -m 700 /tmp/xui-managed-host'
scp -P 22 \
  scripts/install-managed-host \
  scripts/xui-system-update \
  scripts/xui-safe-update \
  scripts/xuiadmin.sudoers \
  secrets/id_ed25519_server1.pub \
  root@SERVER_HOST:/tmp/xui-managed-host/
ssh -p 22 root@SERVER_HOST \
  'chmod 755 /tmp/xui-managed-host/install-managed-host && \
   /tmp/xui-managed-host/install-managed-host /tmp/xui-managed-host/id_ed25519_server1.pub'
```

Проверьте нового пользователя и определённый пакетный менеджер:

```bash
ssh -i secrets/id_ed25519_server1 -p 22 xuiadmin@SERVER_HOST \
  'id; sudo -n /usr/local/sbin/xui-system-update --check; sudo -n -l'
```

## 10. Ручное добавление known_hosts

Сначала сверьте fingerprint через доверенный канал:

```bash
ssh-keyscan -H -p 22 SERVER_HOST > /tmp/server-host-key
ssh-keygen -lf /tmp/server-host-key
cat /tmp/server-host-key >> secrets/known_hosts
chmod 644 secrets/known_hosts
```

Никогда не отключайте StrictHostKeyChecking ради упрощения установки.

## 11. Ручные `.env` и инвентарь

Минимальные значения `.env`:

```dotenv
APP_DOMAIN=xui-admin.example.com
MINI_APP_URL=https://xui-admin.example.com/app/
BOT_TOKEN=...
ALLOWED_TELEGRAM_IDS=[123456789]
SERVERS_FILE=/config/servers.json
SERVER1_PANEL_API_TOKEN=...
```

Минимальный `config/servers.json`:

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
chmod 600 .env config/servers.json
make validate
```

## 12. Панель только через SSH

Интерактивный мастер автоматически создаёт отдельный tunnel service для каждой закрытой панели и задаёт `COMPOSE_FILE`. При ручной настройке начните с примера:

```bash
cp docker-compose.tunnel.example.yml docker-compose.tunnel.yml
```

Заполните параметры и используйте в инвентаре адрес сервиса, например `http://panel-tunnel:28481/secret-path`. Для нескольких панелей создайте отдельные сервисы с уникальными именами.

## 13. Ссылки 3x-ui и итоговая проверка

В Subscription Settings каждой панели задайте внешний Sub Domain и Sub Port. Панель за туннелем должна генерировать публичный адрес, а не localhost или имя Docker-сервиса.

1. Выполните `/servers` в боте.
2. Проверьте `/status SERVER_ID` и `/logs SERVER_ID 30`.
3. Откройте Mini App.
4. Сравните ссылку существующего клиента со ссылкой в 3x-ui.
5. Создайте тестового клиента и проверьте QR.
6. Только после этого запускайте обновление ОС и 3x-ui.
