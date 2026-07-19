.PHONY: bootstrap validate test syntax build up down logs ps security package

bootstrap:
	./scripts/bootstrap.sh

validate:
	python3 scripts/validate-config.py

test:
	python3 -m pytest -q backend/tests

syntax:
	python3 -m compileall -q backend/app
	python3 -m py_compile scripts/validate-config.py
	node --check frontend/app.js
	bash -n scripts/bootstrap.sh scripts/install-managed-host scripts/package-release.sh scripts/security-check.sh scripts/xui-safe-update scripts/xui-system-update

build:
	docker compose build --pull api bot

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=150 api bot caddy

ps:
	docker compose ps

security:
	./scripts/security-check.sh .

package:
	./scripts/package-release.sh
