from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

import asyncssh

from ..config import ServerConfig


STATUS_COMMAND = r"""
set -eu
printf 'uptime_seconds='; awk '{printf "%d\n", $1}' /proc/uptime
printf 'load='; awk '{print $1","$2","$3}' /proc/loadavg
awk '
  /MemTotal:/ {total=$2*1024}
  /MemAvailable:/ {available=$2*1024}
  END {printf "memory=%d,%d,%d\n", total, total-available, available}
' /proc/meminfo
printf 'disk='; df -Pk / | awk 'NR == 2 {gsub(/%/,"",$5); printf "%.0f,%.0f,%.0f,%s\n", $2*1024, $3*1024, $4*1024, $5}'
printf 'xui_service='; {
  if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active x-ui 2>/dev/null || true
  elif command -v rc-service >/dev/null 2>&1; then
    rc-service x-ui status >/dev/null 2>&1 && echo active || echo inactive
  elif command -v service >/dev/null 2>&1; then
    service x-ui status >/dev/null 2>&1 && echo active || echo inactive
  else
    echo unknown
  fi
}
printf 'xui_version='; {
  /usr/local/x-ui/x-ui version 2>/dev/null || true
  /usr/local/x-ui/x-ui -v 2>/dev/null || true
  x-ui version 2>/dev/null || true
  x-ui -v 2>/dev/null || true
} | grep -Eio 'v?[0-9]+([.][0-9]+){1,3}' | tail -n1
printf 'kernel='; uname -sr
os_id=''; os_version=''; os_pretty=''
if [ -r /etc/os-release ]; then
  . /etc/os-release
  os_id="${ID:-}"
  os_version="${VERSION_ID:-}"
  os_pretty="${PRETTY_NAME:-}"
fi
printf 'os_id=%s\n' "$os_id"
printf 'os_version=%s\n' "$os_version"
printf 'os_pretty=%s\n' "$os_pretty"
package_manager=unknown
for candidate in apt-get dnf yum zypper apk pacman; do
  if command -v "$candidate" >/dev/null 2>&1; then
    package_manager=$candidate
    break
  fi
done
printf 'package_manager=%s\n' "$package_manager"
""".strip()

XUI_VERSION_COMMAND = r"""
{
  /usr/local/x-ui/x-ui version 2>/dev/null || true
  /usr/local/x-ui/x-ui -v 2>/dev/null || true
  x-ui version 2>/dev/null || true
  x-ui -v 2>/dev/null || true
} | grep -Eio 'v?[0-9]+([.][0-9]+){1,3}' | tail -n1
""".strip()

UPGRADABLE_PACKAGES_COMMAND = r"""
set -eu
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
if command -v apt >/dev/null 2>&1; then
  apt list --upgradable 2>/dev/null | head -n 250
elif command -v apt-get >/dev/null 2>&1; then
  apt-get --just-print -o Debug::NoLocking=1 upgrade 2>/dev/null | sed -n 's/^Inst /Inst /p' | head -n 250
elif command -v dnf >/dev/null 2>&1; then
  set +e
  output=$(dnf -q check-update 2>&1)
  status=$?
  set -e
  [ "$status" -eq 0 ] || [ "$status" -eq 100 ] || { printf '%s\n' "$output" >&2; exit "$status"; }
  printf '%s\n' "$output" | head -n 250
elif command -v yum >/dev/null 2>&1; then
  set +e
  output=$(yum -q check-update 2>&1)
  status=$?
  set -e
  [ "$status" -eq 0 ] || [ "$status" -eq 100 ] || { printf '%s\n' "$output" >&2; exit "$status"; }
  printf '%s\n' "$output" | head -n 250
elif command -v zypper >/dev/null 2>&1; then
  set +e
  output=$(zypper --non-interactive list-updates 2>&1)
  status=$?
  set -e
  [ "$status" -eq 0 ] || [ "$status" -eq 100 ] || { printf '%s\n' "$output" >&2; exit "$status"; }
  printf '%s\n' "$output" | head -n 250
elif command -v apk >/dev/null 2>&1; then
  apk version -l '<' | head -n 250
elif command -v pacman >/dev/null 2>&1; then
  pacman -Qu | head -n 250
else
  echo 'No supported package manager found (apt, dnf, yum, zypper, apk, pacman)' >&2
  exit 69
fi
""".strip()




class SSHService:
    def __init__(self, server: ServerConfig):
        self.server = server

    async def _connect(self) -> asyncssh.SSHClientConnection:
        return await asyncssh.connect(
            self.server.ssh_host,
            port=self.server.ssh_port,
            username=self.server.ssh_user,
            client_keys=[self.server.ssh_key_path],
            known_hosts=self.server.ssh_known_hosts_path,
            connect_timeout=self.server.ssh_connect_timeout,
            keepalive_interval=30,
            keepalive_count_max=3,
            agent_path=None,
        )

    async def run_fixed(self, command: str, timeout: int = 30) -> str:
        result = await self.run_result(command, timeout=timeout)
        if result.exit_status != 0:
            error = (result.stderr or result.stdout or "SSH command failed").strip()
            raise RuntimeError(error[-4000:])
        return result.stdout

    async def run_result(self, command: str, timeout: int = 30) -> "SSHCommandResult":
        async with await self._connect() as connection:
            result = await asyncio.wait_for(
                connection.run(command, check=False),
                timeout=timeout,
            )
        return SSHCommandResult(
            exit_status=int(result.exit_status),
            stdout=str(result.stdout or ""),
            stderr=str(result.stderr or ""),
        )

    async def xui_logs(self, lines: int = 100) -> str:
        safe_lines = max(10, min(int(lines), 500))
        command = f"""
set -eu
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u x-ui -n {safe_lines} --no-pager -o short-iso
elif [ -r /var/log/x-ui.log ]; then
  tail -n {safe_lines} /var/log/x-ui.log
elif [ -r /var/log/x-ui/x-ui.log ]; then
  tail -n {safe_lines} /var/log/x-ui/x-ui.log
else
  echo 'No supported x-ui log source was found' >&2
  exit 69
fi
""".strip()
        return await self.run_fixed(command, timeout=30)

    async def upgradable_packages(self) -> str:
        return await self.run_fixed(UPGRADABLE_PACKAGES_COMMAND, timeout=120)

    async def run_raw(self, command: str) -> "SSHCommandResult":
        if not self.server.enable_raw_ssh:
            raise RuntimeError("Raw SSH commands are disabled for this server")
        value = command.strip()
        if not value or len(value) > 2000 or "\x00" in value:
            raise RuntimeError("SSH command is empty or too long")
        return await self.run_result(value, timeout=self.server.raw_ssh_timeout)

    async def status(self) -> dict[str, Any]:
        output = await self.run_fixed(STATUS_COMMAND)
        values: dict[str, str] = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()

        load = _float_list(values.get("load", "0,0,0"), 3)
        memory = _int_list(values.get("memory", "0,0,0"), 3)
        disk = _int_list(values.get("disk", "0,0,0,0"), 4)
        return {
            "uptime_seconds": int(float(values.get("uptime_seconds", "0") or 0)),
            "load": {"one": load[0], "five": load[1], "fifteen": load[2]},
            "memory": {"total": memory[0], "used": memory[1], "available": memory[2]},
            "disk": {"total": disk[0], "used": disk[1], "available": disk[2], "percent": disk[3]},
            "xui_service": values.get("xui_service") or "unknown",
            "xui_version": _clean_version(values.get("xui_version", "")),
            "kernel": values.get("kernel", ""),
            "os": {
                "id": values.get("os_id", ""),
                "version": values.get("os_version", ""),
                "pretty": values.get("os_pretty", ""),
                "package_manager": values.get("package_manager", "unknown"),
            },
        }

    async def xui_version(self) -> str:
        output = await self.run_fixed(XUI_VERSION_COMMAND)
        return _clean_version(output.strip())

    async def system_update(self) -> dict[str, Any]:
        command = self.server.system_update_command
        if not command:
            raise RuntimeError("System update command is not configured for this server")
        output = await self.run_fixed(command, timeout=self.server.system_update_timeout)
        reboot_required = "__REBOOT_REQUIRED__=yes" in output
        package_manager_match = re.search(r"^__PACKAGE_MANAGER__=([^\n]+)$", output, re.MULTILINE)
        package_manager = package_manager_match.group(1).strip() if package_manager_match else "unknown"
        clean_output = re.sub(
            r"^__(?:PACKAGE_MANAGER|SYSTEM_UPDATE|REBOOT_REQUIRED)__?=[^\n]*\n?",
            "",
            output,
            flags=re.MULTILINE,
        ).strip()
        return {
            "output": clean_output[-12000:],
            "reboot_required": reboot_required,
            "package_manager": package_manager,
        }

    async def update_panel(self) -> str:
        command = self.server.panel_update_command
        if not command:
            raise RuntimeError("Panel update command is not configured for this server")
        return await self.run_fixed(command, timeout=self.server.panel_update_timeout)


def _int_list(value: str, length: int) -> list[int]:
    result: list[int] = []
    for item in value.split(",")[:length]:
        try:
            result.append(int(item.strip()))
        except ValueError:
            result.append(0)
    return result + [0] * (length - len(result))


def _float_list(value: str, length: int) -> list[float]:
    result: list[float] = []
    for item in value.split(",")[:length]:
        try:
            result.append(float(item.strip()))
        except ValueError:
            result.append(0.0)
    return result + [0.0] * (length - len(result))


def _clean_version(value: str) -> str:
    match = re.search(r"v?\d+(?:\.\d+)+", value)
    return match.group(0) if match else value.strip()


@dataclass(slots=True)
class SSHCommandResult:
    exit_status: int
    stdout: str
    stderr: str
