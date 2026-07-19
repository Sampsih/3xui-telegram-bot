# Usage

[Russian version](usage.md)

## Mini App

The home page shows servers, panel and x-ui availability, operating system details, and client counts. A server page contains system metrics, user management, version information, and update buttons.

### Users

1. Open a server.
2. Select **Users**.
3. Select an inbound.
4. Enter the name, expiration, traffic limit, and device limit.
5. After creation, the connection link and QR code are displayed.

If one client is attached to multiple inbounds, the dialog asks you to select a connection profile. Links come from the 3x-ui API and therefore include Reality, XHTTP, Hysteria2, external proxy, and other panel settings.

### OS update

The button is visible only when `system_update_command` is configured. After confirmation, the backend creates a background job, starts the wrapper through SSH, and stores the result in `data/jobs`.

The wrapper detects the package manager on the server and runs its regular full package update:

| Family | Command |
|---|---|
| Debian, Ubuntu | `apt-get update`, then `apt-get upgrade --with-new-pkgs` |
| Oracle Linux, RHEL, Rocky, Alma | `dnf upgrade --refresh` or `yum update` |
| openSUSE, SLES | `zypper update` |
| Alpine | `apk upgrade` |
| Arch | `pacman -Syu` |

The server is never rebooted automatically. Debian-like systems are checked through `/var/run/reboot-required`; RHEL-like systems use `needs-restarting -r` when available.

### 3x-ui update

The button appears when GitHub reports a newer stable version and `panel_update_command` is configured. Before the operation starts, the database is backed up through the API on the management server and locally on the managed server.

## Telegram commands

```text
/servers
```

Lists server IDs.

```text
/status de-1
```

Shows the service state, version, uptime, load, and disk usage.

```text
/logs de-1 100
```

Shows the last 10–500 lines of the x-ui journal.

```text
/updates de-1
```

Shows packages available in the selected manager's current cache. The command only lists updates and does not refresh package metadata.

```text
/ssh de-1 uname -a
```

Works only when `enable_raw_ssh=true`. The command runs as `xuiadmin`, without a PTY, with a timeout and output limit. Never send passwords, tokens, or keys through Telegram.

## Audit

Mutating operations are written to `data/audit.jsonl`. Raw SSH stores the command hash and exit status, not the command text.

## Backups

API database backups are stored in `data/backups`. Retention is controlled by `BACKUP_RETENTION_DAYS`. Local backups on managed servers are stored in `/var/backups/x-ui`.
