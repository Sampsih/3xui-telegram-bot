# X-UI Telegram Admin

A Telegram Mini App and bot for managing multiple [3x-ui](https://github.com/MHSanaei/3x-ui) servers through the panel API and SSH.

Features include server health, clients and traffic, panel-generated connection links and QR codes, OS/panel updates with backups, Telegram status/log commands, audit logging, and optional unprivileged raw SSH.

## Quick start

```bash
git clone https://github.com/Sampsih/3xui-telegram-bot.git
cd 3xui-telegram-bot
make bootstrap
```

Edit `.env` and `config/servers.json`, provision the dedicated `xuiadmin` account on every managed host, then run:

```bash
make validate
make up
docker compose ps
```

The detailed documentation is currently maintained in Russian:

- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Configuration](docs/configuration.md)
- [Architecture and scaling](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)

Raw SSH is disabled by default and cannot be enabled for `root`. No license has been selected yet; add a `LICENSE` file before distributing the project under open-source terms.
