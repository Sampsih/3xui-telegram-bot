# Architecture and scaling

[Russian version](architecture.md)

## Components

- `bot` — aiogram polling and safe SSH commands;
- `api` — Telegram authentication, 3x-ui API, SSH, jobs, and audit;
- `frontend` — static Telegram Mini App;
- `caddy` — TLS and reverse proxy;
- `panel-tunnel` — optional SSH port forwarding.

## Adding servers

Every server requires one inventory object, one SSH key, and one host key in the shared `known_hosts` file. The code has no fixed server-count limit.

The overview uses a bounded semaphore. Set `SERVER_PROBE_CONCURRENCY` according to the management host capacity and the SSH/panel API limits.

## 3x-ui adapter

All panel access is centralized in `backend/app/services/xui.py`. For a fork with a different API, create a separate client with the same operation set and add a new `panel_type`.

## Operations

Jobs are stored in private JSON files. This is a simple and reliable design for one API instance. For horizontal scaling, replace JobManager with Redis/PostgreSQL and move execution to a dedicated worker. Remote wrappers already use `flock`, protecting each managed server from concurrent updates.

OS updates are not tied to a distribution field in the inventory: the remote wrapper detects the package manager at runtime. When `flock` is unavailable, it uses an atomic lock directory.

## Network

Only Caddy should be public. The API, bot, and tunnels live in Docker networks without host ports. Connect panels to the management host through WireGuard, a private network, or an SSH tunnel.

## Secrets

The current Docker configuration uses a read-only bind mount for `secrets`. Larger installations can replace it with Docker Secrets, SOPS, Vault, or a cloud-provider secret manager without changing the service layer.
