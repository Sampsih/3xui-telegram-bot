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

Raw SSH is disabled by default and cannot be enabled for `root`.

## Support the project

If this project is useful to you, you can support its continued development.

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-support-FFDD00?logo=buymeacoffee&logoColor=000)](https://buymeacoffee.com/sampsih)

### TON (Gram)

Mainnet address:

```text
UQBDpkQH_ryzYKm5iiBQLuFz32SJllk4WI3drZfjQCYFHKX4
```

[Open a transfer in a TON wallet](ton://transfer/UQBDpkQH_ryzYKm5iiBQLuFz32SJllk4WI3drZfjQCYFHKX4?text=Thanks%20for%203xui-telegram-bot) · [Verify the address in TON Viewer](https://tonviewer.com/UQBDpkQH_ryzYKm5iiBQLuFz32SJllk4WI3drZfjQCYFHKX4)

Always verify the recipient address in your wallet before confirming a transfer.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE). You may use, study, modify, and distribute it, including commercially. Distributed copies and derivative works must keep the GPLv3 license and make their complete corresponding source code available.
