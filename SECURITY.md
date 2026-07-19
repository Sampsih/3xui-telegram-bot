# Security Policy

## Сообщение об уязвимости

Не публикуйте рабочие exploits, токены, ключи или данные панелей в обычном issue. Используйте GitHub Private Vulnerability Reporting в разделе Security репозитория. Если владелец fork его не включил, свяжитесь с владельцем приватно.

## Поддерживаемая версия

Security fixes выпускаются только для последнего релиза.

## Обязательные правила эксплуатации

- не используйте root как `ssh_user`;
- не включайте raw SSH без отдельной оценки риска;
- храните панель за firewall/private network/tunnel;
- включайте TLS verification для публичных HTTPS-панелей;
- регулярно ротируйте Telegram token, panel credentials и SSH keys;
- проверяйте fingerprints до добавления `known_hosts`;
- не публикуйте `.env`, `config/servers.json`, `secrets`, `data` и backups.
