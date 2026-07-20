import base64
import asyncio
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from pydantic import SecretStr

from app.auth import validate_telegram_init_data
from app.config import ServerConfig, Settings, get_settings
from app.models import ClientCreate
from app.services.links import build_connection, connection_payload
from app.services.jobs import JobManager
from app.services.version import summarize_release_notes
from app.services.ssh import SSHService
from app.services.xui import XUIClient, _extract_connection_links


def test_telegram_init_data_signature():
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "AAE",
        "user": json.dumps({"id": 123, "first_name": "Lex"}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", b"test-token", hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    assert validate_telegram_init_data(urlencode(values), "test-token", 3600).id == 123


def test_reality_link_derives_public_key():
    private = X25519PrivateKey.generate()
    private_raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    private_b64 = base64.urlsafe_b64encode(private_raw).decode().rstrip("=")
    public_raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    public_b64 = base64.urlsafe_b64encode(public_raw).decode().rstrip("=")
    server = ServerConfig(
        id="nl", name="NL", ssh_host="127.0.0.1", ssh_user="u", ssh_key_path="/k",
        ssh_known_hosts_path="/h", panel_url="https://panel.local/path", panel_api_token=SecretStr("token"), public_host="vpn.example.com",
    )
    inbound = {
        "id": 1, "protocol": "vless", "port": 443,
        "settings": json.dumps({"clients": [{"id": "11111111-1111-1111-1111-111111111111", "email": "lex", "flow": "xtls-rprx-vision"}]}),
        "streamSettings": json.dumps({"network": "tcp", "security": "reality", "realitySettings": {"privateKey": private_b64, "serverNames": ["example.com"], "shortIds": ["abcd"]}}),
    }
    result = build_connection(server, inbound, "lex")
    assert f"pbk={public_b64}" in result["uri"]
    assert result["qr_data_url"].startswith("data:image/png;base64,")


def test_hysteria2_link_uses_password_auth_and_tls_options():
    server = ServerConfig(
        id="ru",
        name="RU",
        ssh_host="127.0.0.1",
        ssh_user="u",
        ssh_key_path="/k",
        ssh_known_hosts_path="/h",
        panel_url="https://panel.local/path",
        panel_api_token=SecretStr("token"),
        public_host="vpn.example.com",
    )
    inbound = {
        "id": 7,
        "protocol": "hysteria",
        "port": 443,
        "settings": json.dumps({
            "clients": [{"email": "lex", "password": "p@ss:word"}],
            "obfs": {"type": "salamander", "salamander": {"password": "obfs secret"}},
        }),
        "streamSettings": json.dumps({
            "security": "tls",
            "tlsSettings": {"serverName": "cdn.example.com", "allowInsecure": True},
        }),
    }
    result = build_connection(server, inbound, "lex")
    assert result["uri"].startswith("hysteria2://p%40ss%3Aword@vpn.example.com:443/")
    assert "sni=cdn.example.com" in result["uri"]
    assert "insecure=1" in result["uri"]
    assert "obfs=salamander" in result["uri"]
    assert "obfs-password=obfs+secret" in result["uri"]
    assert result["qr_data_url"].startswith("data:image/png;base64,")


def test_hysteria2_does_not_use_email_as_username():
    server = ServerConfig(
        id="nl",
        name="NL",
        ssh_host="127.0.0.1",
        ssh_user="u",
        ssh_key_path="/k",
        ssh_known_hosts_path="/h",
        panel_url="http://nl-tunnel:28481/path",
        panel_username="admin",
        panel_password=SecretStr("secret"),
        panel_verify_tls=False,
        public_host="2001:db8::1",
    )
    inbound = {
        "id": 8,
        "protocol": "hysteria2",
        "port": 8443,
        "settings": json.dumps({"clients": [{"email": "display-name", "password": "only-password"}]}),
        "streamSettings": "{}",
    }
    result = build_connection(server, inbound, "display-name")
    assert result["uri"].startswith("hysteria2://only-password@[2001:db8::1]:8443/")
    assert "display-name%3A" not in result["uri"]


def test_panel_generated_links_are_preserved_and_deduplicated():
    first = "vless://user@example.com:443?security=reality#Primary"
    second = "hysteria2://password@example.com:443/?sni=example.com#UDP"
    payload = {"obj": [first, {"links": f"{second}\n{first}"}]}
    assert _extract_connection_links(payload) == [first, second]
    connection = connection_payload(second)
    assert connection["uri"] == second
    assert connection["protocol"] == "hysteria2"
    assert connection["label"] == "UDP"
    assert connection["qr_data_url"].startswith("data:image/png;base64,")


def test_raw_ssh_cannot_be_enabled_for_root():
    try:
        ServerConfig(
            id="unsafe",
            name="Unsafe",
            ssh_host="127.0.0.1",
            ssh_user="root",
            ssh_key_path="/k",
            ssh_known_hosts_path="/h",
            panel_url="https://panel.local/path",
            panel_api_token=SecretStr("token"),
            enable_raw_ssh=True,
        )
    except ValueError as exc:
        assert "root" in str(exc)
    else:
        raise AssertionError("root raw SSH configuration must be rejected")


def test_vless_flow_is_opt_in():
    assert ClientCreate(inbound_id=1, email="client").flow == ""


def test_client_creation_falls_back_to_current_3xui_api():
    server = ServerConfig(
        id="new-panel",
        name="New panel",
        ssh_host="127.0.0.1",
        ssh_user="u",
        ssh_key_path="/k",
        ssh_known_hosts_path="/h",
        panel_url="https://panel.local/secret",
        panel_api_token=SecretStr("token"),
    )
    calls = []
    created_client = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal created_client
        path = request.url.path
        calls.append(path)
        if path.endswith("/panel/api/inbounds/get/7"):
            clients = [created_client] if created_client else []
            inbound = {"id": 7, "protocol": "vless", "settings": json.dumps({"clients": clients})}
            return httpx.Response(200, json={"success": True, "obj": inbound})
        if path.endswith("/panel/api/inbounds/addClient"):
            return httpx.Response(404)
        if path.endswith("/panel/api/clients/add"):
            payload = json.loads(request.content)
            assert payload["inboundIds"] == [7]
            assert payload["client"]["email"] == "new-user"
            assert payload["client"]["security"] == "auto"
            assert payload["client"]["tgId"] == 0
            created_client = payload["client"]
            return httpx.Response(200, json={"success": True, "obj": {}})
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    async def scenario():
        panel = XUIClient(server)
        await panel.client.aclose()
        panel.client = httpx.AsyncClient(
            base_url=panel.base_url + "/",
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await panel.add_client(ClientCreate(inbound_id=7, email="new-user"))
            assert result["client"]["email"] == "new-user"
        finally:
            await panel.client.aclose()

    asyncio.run(scenario())
    assert any(path.endswith("/panel/api/inbounds/addClient") for path in calls)
    assert any(path.endswith("/panel/api/clients/add") for path in calls)


def test_current_3xui_delete_detaches_client_used_by_other_inbounds():
    server = ServerConfig(
        id="new-panel",
        name="New panel",
        ssh_host="127.0.0.1",
        ssh_user="u",
        ssh_key_path="/k",
        ssh_known_hosts_path="/h",
        panel_url="https://panel.local/secret",
        panel_api_token=SecretStr("token"),
    )
    attached = {7, 8}
    client = {"id": "11111111-1111-1111-1111-111111111111", "email": "shared-user"}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/panel/api/inbounds/get/7"):
            clients = [client] if 7 in attached else []
            inbound = {"id": 7, "protocol": "vless", "settings": json.dumps({"clients": clients})}
            return httpx.Response(200, json={"success": True, "obj": inbound})
        if path.endswith("/panel/api/inbounds/7/delClient/11111111-1111-1111-1111-111111111111"):
            return httpx.Response(404)
        if path.endswith("/panel/api/clients/get/shared-user"):
            return httpx.Response(200, json={"success": True, "obj": {"client": client, "inboundIds": sorted(attached)}})
        if path.endswith("/panel/api/clients/shared-user/detach"):
            assert json.loads(request.content) == {"inboundIds": [7]}
            attached.discard(7)
            return httpx.Response(200, json={"success": True})
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    async def scenario():
        panel = XUIClient(server)
        await panel.client.aclose()
        panel.client = httpx.AsyncClient(
            base_url=panel.base_url + "/",
            transport=httpx.MockTransport(handler),
        )
        try:
            await panel.delete_client_by_email(7, "shared-user")
        finally:
            await panel.client.aclose()

    asyncio.run(scenario())
    assert attached == {8}


def test_release_notes_summary_limits_bullets():
    notes = "# Release\n" + "\n".join(f"- Item {index}" for index in range(50)) + "\nFull Changelog: old...new"
    summary = summarize_release_notes(notes, max_items=3)
    assert summary.count("• ") == 3
    assert "Full Changelog" not in summary


def test_background_job_persists_result(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "[1]")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    async def scenario():
        manager = JobManager()
        job = await manager.create("ru", "test", 1)

        async def operation():
            return {"success": True, "output": "done"}

        manager.start(job["id"], operation())
        for _ in range(100):
            current = await manager.get(job["id"], "ru")
            if current and current["status"] == "succeeded":
                assert current["result"]["output"] == "done"
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("background job did not finish")

    try:
        asyncio.run(scenario())
    finally:
        get_settings.cache_clear()


def test_system_update_result_extracts_manager_and_internal_markers():
    server = ServerConfig(
        id="ol-1",
        name="Oracle Linux",
        ssh_host="127.0.0.1",
        ssh_user="xuiadmin",
        ssh_key_path="/k",
        ssh_known_hosts_path="/h",
        panel_url="https://panel.local/path",
        panel_api_token=SecretStr("token"),
        system_update_command="sudo -n /usr/local/sbin/xui-system-update",
    )
    service = SSHService(server)

    async def fake_run_fixed(command, timeout=30):
        assert command == server.system_update_command
        assert timeout == server.system_update_timeout
        return "Updated packages\n__PACKAGE_MANAGER__=dnf\n__SYSTEM_UPDATE__=complete\n__REBOOT_REQUIRED__=yes\n"

    service.run_fixed = fake_run_fixed
    result = asyncio.run(service.system_update())
    assert result == {
        "output": "Updated packages",
        "reboot_required": True,
        "package_manager": "dnf",
    }


def test_servers_file_loads_inventory_and_expands_secret(monkeypatch, tmp_path):
    inventory = tmp_path / "servers.json"
    inventory.write_text(
        json.dumps([
            {
                "id": "edge-1",
                "name": "Edge 1",
                "ssh_host": "192.0.2.10",
                "ssh_user": "xuiadmin",
                "ssh_key_path": "/run/secrets/id_ed25519_edge1",
                "ssh_known_hosts_path": "/run/secrets/known_hosts",
                "panel_url": "https://panel.example.com/path",
                "panel_api_token": "${EDGE_PANEL_TOKEN}",
            }
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv("EDGE_PANEL_TOKEN", "secret-token")
    settings = Settings(
        _env_file=None,
        bot_token="test-token",
        allowed_telegram_ids=[1],
        servers_file=str(inventory),
    )
    assert [server.id for server in settings.servers] == ["edge-1"]
    assert settings.servers[0].panel_api_token.get_secret_value() == "secret-token"


def test_servers_file_rejects_duplicate_ids(monkeypatch, tmp_path):
    inventory = tmp_path / "servers.json"
    server = {
        "id": "duplicate",
        "name": "Duplicate",
        "ssh_host": "192.0.2.20",
        "ssh_user": "xuiadmin",
        "ssh_key_path": "/run/secrets/key",
        "ssh_known_hosts_path": "/run/secrets/known_hosts",
        "panel_url": "https://panel.example.com/path",
        "panel_api_token": "token",
    }
    inventory.write_text(json.dumps([server, server]), encoding="utf-8")
    try:
        Settings(
            _env_file=None,
            bot_token="test-token",
            allowed_telegram_ids=[1],
            servers_file=str(inventory),
        )
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate server IDs must be rejected")
