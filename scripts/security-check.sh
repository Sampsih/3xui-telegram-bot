#!/usr/bin/env bash
set -Eeuo pipefail

cd "${1:-/opt/xui-telegram-admin}"
fail=0
warn() { printf 'WARN: %s\n' "$*"; }
ok() { printf 'OK: %s\n' "$*"; }
bad() { printf 'FAIL: %s\n' "$*"; fail=1; }

[[ -f .env ]] || bad '.env is missing'
if [[ -f .env ]]; then
  mode=$(stat -c '%a' .env)
  if [[ "$mode" == "600" ]]; then
    ok '.env mode is 600'
  else
    bad ".env mode is $mode, expected 600"
  fi
  if grep -Eq '^DEV_BYPASS_AUTH=false$' .env; then
    ok 'DEV_BYPASS_AUTH is false'
  else
    bad 'DEV_BYPASS_AUTH must be false'
  fi
  if grep -Eq '^ENABLE_API_DOCS=false$' .env; then
    ok 'API docs are disabled'
  else
    warn 'Set ENABLE_API_DOCS=false'
  fi
fi

for key in secrets/id_ed25519_*; do
  [[ -e "$key" ]] || continue
  mode=$(stat -c '%a' "$key")
  if [[ "$mode" == "600" ]]; then
    ok "$key mode is 600"
  else
    bad "$key mode is $mode, expected 600"
  fi
done

if [[ -f secrets/known_hosts ]]; then
  mode=$(stat -c '%a' secrets/known_hosts)
  if [[ "$mode" == "644" || "$mode" == "600" ]]; then
    ok 'known_hosts permissions are acceptable'
  else
    warn "known_hosts mode is $mode"
  fi
fi

if command -v docker >/dev/null 2>&1; then
  if docker compose config -q; then
    ok 'Docker Compose configuration parses'
  else
    bad 'Docker Compose configuration is invalid'
  fi
  if docker compose config 2>/dev/null | grep -q '/var/run/docker.sock'; then
    bad 'Docker socket is mounted into a service'
  else
    ok 'Docker socket is not mounted'
  fi
  if docker compose config 2>/dev/null | sed -n '/bot:/,/^[^ ]/p' | grep -q '/run/secrets'; then
    warn 'Bot service can see SSH secrets for chat commands; every server must use a dedicated non-root ssh_user'
  else
    ok 'Bot service does not mount SSH secrets'
  fi
else
  warn 'Docker is not installed or not in PATH'
fi

if ss -lnt 2>/dev/null | grep -Eq ':(8000|28481)[[:space:]]'; then
  warn 'A management port is listening on the host; only 80/443 should be public'
else
  ok 'Management ports 8000 and 28481 are not host-listening'
fi

exit "$fail"
