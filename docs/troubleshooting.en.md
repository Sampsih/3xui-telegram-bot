# Troubleshooting

[Russian version](troubleshooting.md)

## `error parsing value for field servers`

Validate the JSON:

```bash
python3 -m json.tool config/servers.json >/dev/null
make validate
```

JSON requires a comma after every field except the last field before `}`.

## `ssh_known_hosts_path Field required`

Add this to every server:

```json
"ssh_known_hosts_path": "/run/secrets/known_hosts"
```

## `Host key verification failed`

Do not use `StrictHostKeyChecking=no`. Verify the fingerprint and update `secrets/known_hosts`.

## `Permission denied (publickey)`

Check the username, key path, and permissions:

```bash
chmod 600 secrets/id_ed25519_*
ssh -i secrets/id_ed25519_server1 xuiadmin@SERVER_HOST id
```

## sudoers error `unknown setting: requiretty`

The current `scripts/xuiadmin.sudoers` does not contain `requiretty`. Copy the file again and rerun `install-managed-host`.

## The OS update button is missing

Check that `system_update_command` exists in the server object, then recreate `api` and `bot`.

## The 3x-ui update button is missing

It is displayed only when the wrapper is configured and a newer stable release is available.

## A link contains `localhost` or a tunnel-container name

Configure the external Sub Domain/Sub Port in 3x-ui Subscription Settings.

## The Mini App returns 401

Open it through the bot button. Check `BOT_TOKEN`, `MINI_APP_URL`, the server clock, and the `initData` age.

## `/logs` returns no output

Rerun `install-managed-host`: it adds `xuiadmin` to the `systemd-journal` group. Then establish a new SSH session.

## Container diagnostics

```bash
docker compose ps
docker compose logs --tail=200 api bot caddy
curl -i https://YOUR_DOMAIN/health
curl -i https://YOUR_DOMAIN/ready
```
