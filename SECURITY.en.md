# Security Policy

[Russian version](SECURITY.md)

## Reporting a vulnerability

Do not post working exploits, tokens, keys, or panel data in a regular issue. Use GitHub Private Vulnerability Reporting in the repository's Security section. If the fork owner has not enabled it, contact the owner privately.

## Supported version

Security fixes are released only for the latest release.

## Mandatory operating rules

- do not use root as `ssh_user`;
- do not enable raw SSH without a separate risk assessment;
- keep the panel behind a firewall, private network, or tunnel;
- enable TLS verification for public HTTPS panels;
- rotate the Telegram token, panel credentials, and SSH keys regularly;
- verify fingerprints before adding entries to `known_hosts`;
- never publish `.env`, `config/servers.json`, `secrets`, `data`, or backups.
