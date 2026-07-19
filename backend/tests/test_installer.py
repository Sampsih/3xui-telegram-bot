import importlib.util
from pathlib import Path


INSTALLER_PATH = Path(__file__).parents[2] / "scripts" / "interactive_install.py"
SPEC = importlib.util.spec_from_file_location("interactive_install", INSTALLER_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_parse_telegram_ids_deduplicates_values():
    assert installer.parse_telegram_ids("123, 456,123") == [123, 456]


def test_parse_telegram_ids_rejects_non_numeric_values():
    try:
        installer.parse_telegram_ids("123, admin")
    except ValueError as exc:
        assert "positive integers" in str(exc)
    else:
        raise AssertionError("non-numeric Telegram IDs must be rejected")


def test_dotenv_quote_keeps_special_characters_literal():
    assert installer.dotenv_quote("p$a's\\word") == "'p$a\\'s\\\\word'"


def test_render_tunnel_compose_scales_to_multiple_servers():
    rendered = installer.render_tunnel_compose(
        [
            {"id": "de-1", "ssh_host": "203.0.113.10", "ssh_port": 22, "panel_port": 2053},
            {"id": "nl-1", "ssh_host": "203.0.113.20", "ssh_port": 2222, "panel_port": 28481},
        ]
    )
    assert "panel-tunnel-de-1:" in rendered
    assert "panel-tunnel-nl-1:" in rendered
    assert "/run/secrets/id_ed25519_de-1" in rendered
    assert "0.0.0.0:28481:127.0.0.1:28481" in rendered


def test_validate_host_accepts_linux_server_addresses():
    assert installer.validate_host("vpn.example.com")
    assert installer.validate_host("203.0.113.10")
    assert installer.validate_host("2001:db8::10")
    assert not installer.validate_host("bad host")


def test_tls_verification_may_only_be_disabled_for_private_panels():
    assert installer.may_disable_tls_verification("http://panel.example.com/path")
    assert installer.may_disable_tls_verification("https://10.0.0.5/path")
    assert installer.may_disable_tls_verification("https://panel-tunnel-de-1:2053/path")
    assert not installer.may_disable_tls_verification("https://panel.example.com/path")
