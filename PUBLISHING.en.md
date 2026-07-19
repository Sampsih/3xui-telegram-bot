# First GitHub publication

[Russian version](PUBLISHING.md)

## Before publication

1. Verify that `LICENSE` exists: the project is distributed under GNU GPLv3.
2. Run the checks:

```bash
make bootstrap
make validate
make test
make syntax
docker compose config -q
```

3. Confirm that `git status --ignored` shows `.env`, `config/servers.json`, `data`, and secrets as ignored.
4. Perform an additional search for your domains, IP addresses, usernames, and tokens before the first commit.

## Create the repository

Create an empty GitHub repository without automatically generated README, `.gitignore`, or license files. Then run:

```bash
git init
git add .
git status
git commit -m "Initial public release"
git branch -M main
git remote add origin git@github.com:Sampsih/3xui-telegram-bot.git
git push -u origin main
```

## GitHub settings

- enable Private Vulnerability Reporting;
- enable Dependabot alerts and security updates;
- protect `main` by requiring the successful `CI` workflow;
- prohibit force pushes and deletion of `main`;
- add a description, topics, and documentation link;
- use release tags in the `v4.1.0` format.

## Next release

Update `VERSION` and `CHANGELOG.md`, run all checks, then:

```bash
make package
git tag -a v4.1.0 -m "v4.1.0"
git push origin main v4.1.0
```

The archive and SHA-256 file are created in `dist/` and can be attached to the GitHub Release.
