# Первая публикация на GitHub

[English version](PUBLISHING.en.md)

## До публикации

1. Проверьте наличие файла `LICENSE`: проект распространяется по GNU GPLv3.
2. Запустите проверки:

```bash
make bootstrap
make validate
make test
make syntax
docker compose config -q
```

3. Убедитесь, что `git status --ignored` показывает `.env`, `config/servers.json`, `data` и секреты как ignored.
4. Выполните дополнительный поиск собственных доменов, IP, логинов и токенов перед первым commit.

## Создание репозитория

Создайте на GitHub пустой репозиторий без автоматически добавленных README, `.gitignore` и лицензии. Затем:

```bash
git init
git add .
git status
git commit -m "Initial public release"
git branch -M main
git remote add origin git@github.com:Sampsih/3xui-telegram-bot.git
git push -u origin main
```

## Настройки GitHub

- включите Private vulnerability reporting;
- включите Dependabot alerts и security updates;
- защитите `main`, потребовав успешный workflow `CI`;
- запретите force push и удаление `main`;
- добавьте описание, topics и ссылку на документацию;
- создавайте релизные теги в формате `v4.1.0`.

## Следующий релиз

Обновите `VERSION` и `CHANGELOG.md`, запустите проверки, затем:

```bash
make package
git tag -a v4.1.0 -m "v4.1.0"
git push origin main v4.1.0
```

Архив и SHA-256 будут созданы в `dist/` и могут быть приложены к GitHub Release.
