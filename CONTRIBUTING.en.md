# Contributing

[Russian version](CONTRIBUTING.md)

1. Create an issue describing the task or bug.
2. Create a separate branch.
3. Do not add secrets or real client links.
4. Add a test for the behavior being changed.
5. Run `make validate`, `make test`, and `make syntax`.
6. In the pull request, describe compatibility with the 3x-ui version and the manual verification procedure.

Use anonymized fixtures for panel API changes. UUIDs, client passwords, Reality keys, Telegram tokens, real server IP addresses, and `x-ui.db` contents are prohibited in issues and commits.

Changes to update wrappers require especially careful review because they run through sudo on managed servers.
