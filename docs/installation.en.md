# Installation

[Russian version](installation.md)

## 1. Requirements

- a dedicated Linux host for the application;
- Docker Engine and Docker Compose v2;
- a domain pointing to the application host;
- open TCP ports 80 and 443;
- a Telegram bot created through BotFather;
- root access for the initial preparation of every managed server;
- an installed MHSanaei/3x-ui panel.

After provisioning, the application does not use root SSH. A dedicated `xuiadmin` user is created for it.

## 2. Get the project

```bash
git clone https://github.com/Sampsih/3xui-telegram-bot.git
cd 3xui-telegram-bot
make bootstrap
```

This creates:

- `.env` from the public example;
- `config/servers.json` from the inventory example;
- private `data` and `secrets` directories.

## 3. Telegram

1. Create a bot through BotFather.
2. Store its token in `BOT_TOKEN`.
3. Add the numeric Telegram IDs of all administrators to `ALLOWED_TELEGRAM_IDS`.
4. After deployment, configure the Main Mini App or Menu Button as `https://APP_DOMAIN/app/`.

## 4. SSH keys

Create a separate key for every server:

```bash
ssh-keygen -t ed25519 -f secrets/id_ed25519_server1 -C xuiadmin-server1
chmod 600 secrets/id_ed25519_server1
chmod 644 secrets/id_ed25519_server1.pub
```

From the management host, copy the installer, wrappers, sudoers policy, and public key to a temporary directory on the managed server:

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

The script creates `xuiadmin`, installs the update wrappers, and validates sudoers.

If SSH uses a nonstandard port, add `-p PORT` to `ssh` and `-P PORT` to `scp`.

Verify access:

```bash
ssh -i secrets/id_ed25519_server1 xuiadmin@SERVER_HOST \
  'id; systemctl is-active x-ui; sudo -n -l'
```

## 5. known_hosts

Never disable host-key verification. First verify the server fingerprint through a trusted channel, then add the key:

```bash
ssh-keyscan -H -p 22 SERVER_HOST >> secrets/known_hosts
chmod 644 secrets/known_hosts
```

## 6. `.env`

```bash
nano .env
chmod 600 .env
```

Required values:

```dotenv
APP_DOMAIN=xui-admin.example.com
MINI_APP_URL=https://xui-admin.example.com/app/
BOT_TOKEN=...
ALLOWED_TELEGRAM_IDS=[123456789]
SERVERS_FILE=/config/servers.json
```

Panel secrets can be stored in separate variables and referenced from the inventory as `${VARIABLE_NAME}`.

## 7. Server inventory

Open `config/servers.json`. Remove unused examples and fill in one object for every server. Minimal example:

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

## 8. SSH-only panel

Copy the overlay:

```bash
cp docker-compose.tunnel.example.yml docker-compose.tunnel.yml
```

Fill in `TUNNEL_*` in `.env` and use an inventory URL such as:

```text
http://panel-tunnel:28481/secret-path
```

Start with the overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

For multiple private panels, create one tunnel service per panel with a unique service name and local port, or use WireGuard/private networking.

## 9. Start the application

```bash
docker compose config -q
docker compose build --pull api bot
docker compose up -d
docker compose ps
docker compose logs --tail=150 api bot caddy
```

Checks:

```bash
curl -fsS https://YOUR_DOMAIN/health
curl -fsS https://YOUR_DOMAIN/ready
```

`/health` verifies the process; `/ready` verifies that servers are configured and the data directory is available.

## 10. Configure 3x-ui links

Set the external Sub Domain and Sub Port in Subscription Settings on every panel. This is mandatory for panels behind an SSH tunnel: 3x-ui must generate a public address, not `localhost` or a Docker service name.

## 11. Post-deployment verification

1. Open the bot and run `/servers`.
2. Check `/status SERVER_ID` and `/logs SERVER_ID 30`.
3. Open the Mini App.
4. Compare an existing client's link with the link shown by 3x-ui.
5. Create a test client and verify its QR code.
6. Only then test update operations.
