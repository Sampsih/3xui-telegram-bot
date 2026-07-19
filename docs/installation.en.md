# Installation

[Russian version](installation.md)

## 1. Requirements

- any Linux application host with Docker Engine and Docker Compose v2;
- Python 3 and an OpenSSH client for interactive setup;
- a domain pointing to the application host and open TCP ports 80/443;
- a Telegram bot created through BotFather;
- SSH access to the managed servers;
- root or sudo access only for their initial provisioning;
- an installed MHSanaei/3x-ui panel;
- a managed Linux OS with `systemctl`, `rc-service`, or `service` and `apt-get`, `dnf`, `yum`, `zypper`, `apk`, or `pacman`.

After provisioning, the application connects as the dedicated unprivileged `xuiadmin` user, not root.

## 2. Get the project

```bash
git clone https://github.com/Sampsih/3xui-telegram-bot.git
cd 3xui-telegram-bot
```

## 3. Interactive installation

Recommended method:

```bash
make install
```

The installer asks for:

- the wizard language;
- the domain, bot token, and administrator Telegram IDs;
- the number of managed servers;
- the ID, name, and location of each server;
- the SSH address and port;
- the public host used in connection links;
- a direct panel URL or SSH tunnel parameters;
- an API token or panel username and password;
- whether to enable OS, 3x-ui, and raw SSH updates;
- whether to provision the remote host and start Compose immediately.

The script creates private `.env`, `config/servers.json`, separate keys under `secrets`, shared `known_hosts`, and, when required, `docker-compose.tunnel.yml`. Existing configuration is backed up under `data/installer-backups` before replacement.

## 4. Host key verification and server provisioning

For every server, the wizard obtains the host key, displays its fingerprint through `ssh-keygen -lf`, and adds it only after you confirm verification through a trusted channel. Do not accept an unknown fingerprint.

With your permission, the wizard copies `install-managed-host`, `xui-system-update`, `xui-safe-update`, and the public key to the server. The remote script creates `xuiadmin`, restricted sudoers rules, and automatically detects the package manager.

Initial SSH authentication may use root or a sudo-capable account. This operation does not copy its passwords or private keys into the project.

## 5. Start the application

If startup was skipped in the wizard:

```bash
make validate
docker compose config -q
docker compose up -d --build
docker compose ps
```

Checks:

```bash
curl -fsS https://YOUR_DOMAIN/health
curl -fsS https://YOUR_DOMAIN/ready
```

`/health` checks the process; `/ready` checks that servers are configured and the data directory is accessible.

## 6. Telegram

1. Create the bot through BotFather.
2. Confirm that its token is stored in `BOT_TOKEN`.
3. Confirm that numeric administrator Telegram IDs are present in `ALLOWED_TELEGRAM_IDS`.
4. Set the Main Mini App or Menu Button to the URL from `MINI_APP_URL`.

## 7. Completely manual setup

If the interactive wizard is not needed:

```bash
make bootstrap
```

This creates:

- `.env` from the public example;
- `config/servers.json` from the example inventory;
- private `data` and `secrets` directories.

## 8. Create an SSH key manually

Create a separate key for each server:

```bash
ssh-keygen -t ed25519 -N '' -f secrets/id_ed25519_server1 -C xuiadmin-server1
chmod 600 secrets/id_ed25519_server1
chmod 644 secrets/id_ed25519_server1.pub
```

## 9. Provision a managed host manually

Copy the installer, wrappers, sudoers file, and public key into a temporary directory:

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

Verify the new account and detected package manager:

```bash
ssh -i secrets/id_ed25519_server1 -p 22 xuiadmin@SERVER_HOST \
  'id; sudo -n /usr/local/sbin/xui-system-update --check; sudo -n -l'
```

## 10. Add known_hosts manually

First verify the fingerprint through a trusted channel:

```bash
ssh-keyscan -H -p 22 SERVER_HOST > /tmp/server-host-key
ssh-keygen -lf /tmp/server-host-key
cat /tmp/server-host-key >> secrets/known_hosts
chmod 644 secrets/known_hosts
```

Never disable StrictHostKeyChecking to simplify installation.

## 11. Manual `.env` and inventory

Minimum `.env` values:

```dotenv
APP_DOMAIN=xui-admin.example.com
MINI_APP_URL=https://xui-admin.example.com/app/
BOT_TOKEN=...
ALLOWED_TELEGRAM_IDS=[123456789]
SERVERS_FILE=/config/servers.json
SERVER1_PANEL_API_TOKEN=...
```

Minimum `config/servers.json`:

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

## 12. Panel available only through SSH

The interactive wizard automatically creates a dedicated tunnel service for every private panel and sets `COMPOSE_FILE`. For manual setup, start with the example:

```bash
cp docker-compose.tunnel.example.yml docker-compose.tunnel.yml
```

Fill in its parameters and use the service address in the inventory, for example `http://panel-tunnel:28481/secret-path`. For multiple panels, create separate services with unique names.

## 13. 3x-ui links and final verification

Set the external Sub Domain and Sub Port in each panel's Subscription Settings. A tunneled panel must generate a public address, not localhost or a Docker service name.

1. Run `/servers` in the bot.
2. Check `/status SERVER_ID` and `/logs SERVER_ID 30`.
3. Open the Mini App.
4. Compare an existing client's connection link with the 3x-ui link.
5. Create a test client and verify its QR code.
6. Only then run OS and 3x-ui updates.
