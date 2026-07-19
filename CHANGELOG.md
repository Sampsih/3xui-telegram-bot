# Changelog

## 1.1.0

- Added package updates for Debian/Ubuntu, Oracle Linux/RHEL/Rocky/Alma, openSUSE/SLES, Alpine, and Arch families.
- Added runtime detection for `apt-get`, `dnf`, `yum`, `zypper`, `apk`, and `pacman`.
- Added systemd, OpenRC, and generic service-status support.
- Added a bilingual interactive installer for application settings and any number of managed servers.
- Added automatic SSH key creation, verified `known_hosts` enrollment, optional remote provisioning, and multi-tunnel Compose generation.

## 1.0.0 — First public release

- Added scalable `SERVERS_FILE` inventory with environment secret references.
- Added bounded server overview concurrency.
- Added `/ready` readiness endpoint and Docker health checks.
- Added hardened generic Compose and optional SSH tunnel overlay.
- Added bootstrap, configuration validation and release packaging commands.
- Added complete bilingual user, operator and contributor documentation with automated RU/EN parity checks.
- Added GitHub Actions CI, Dependabot and issue templates.
- Switched connection links to the 3x-ui `subLinks` API.
- Added multiple connection profiles and QR selection.
- Added persisted background update jobs.
- Added Telegram SSH status, logs and package commands.
- Added optional unprivileged raw SSH.
- Added safe managed-host provisioning and update wrappers.
