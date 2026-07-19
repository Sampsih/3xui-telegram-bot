# Configuration

[Russian version](configuration.md)

## Application settings

| Variable | Purpose | Default |
|---|---|---|
| `APP_DOMAIN` | Caddy domain | required |
| `MINI_APP_URL` | Full `/app/` URL | required |
| `BOT_TOKEN` | BotFather token | required |
| `ALLOWED_TELEGRAM_IDS` | JSON array of administrators | required |
| `AUTH_MAX_AGE_SECONDS` | Maximum initData age | `900` |
| `SERVERS_FILE` | Server inventory path inside the container | `/config/servers.json` |
| `SERVER_PROBE_CONCURRENCY` | Concurrent overview probes | `10` |
| `BACKUP_RETENTION_DAYS` | API backup retention | `30` |
| `BOT_OUTPUT_MAX_CHARS` | SSH output limit in Telegram | `12000` |
| `ENABLE_API_DOCS` | Swagger at `/api/docs` | `false` |
| `DEV_BYPASS_AUTH` | Local Telegram bypass | `false` |

`DEV_BYPASS_AUTH` is permitted only with a localhost Mini App URL.

## Server fields

| Field | Description |
|---|---|
| `id` | Unique stable ID: `a-z0-9_-` |
| `name` | Display name |
| `location` | Location |
| `ssh_host`, `ssh_port` | SSH endpoint |
| `ssh_user` | Only `xuiadmin` is recommended |
| `ssh_key_path` | Path inside the container |
| `ssh_known_hosts_path` | Usually `/run/secrets/known_hosts` |
| `panel_url` | URL including the secret web base path |
| `panel_api_token` | Preferred authentication method |
| `panel_username`, `panel_password` | Session-login fallback |
| `panel_verify_tls` | TLS verification; disable only for private/tunnel HTTP(S) |
| `public_host` | Fallback address used by the legacy link generator |
| `system_update_command` | Fixed OS-update wrapper |
| `panel_update_command` | Fixed panel-update wrapper |
| `enable_raw_ssh` | Enable `/ssh`; prohibited with `root` |
| `raw_ssh_timeout` | Raw SSH timeout, maximum 600 seconds |

The inventory does not declare an OS type. The backend reads `/etc/os-release`, while wrappers automatically select the first available manager from `apt-get`, `dnf`, `yum`, `zypper`, `apk`, and `pacman`.

## Environment-variable references

JSON supports a complete string value in the form `${VARIABLE_NAME}`:

```json
"panel_api_token": "${DE_PANEL_TOKEN}"
```

The variable must exist in the container environment. Partial interpolation inside a string is not performed.

## Legacy format

`SERVERS=[{...}]` in `.env` remains supported. Using `SERVERS` and `SERVERS_FILE` at the same time is prohibited to avoid ambiguity.
