from __future__ import annotations

import asyncio
import hashlib
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, WebAppInfo

from .config import get_settings
from .models import TelegramUser
from .audit import write_audit
from .services.ssh import SSHService

settings = get_settings()
dp = Dispatcher()


def _allowed(user_id: int) -> bool:
    return bool(settings.allowed_telegram_ids) and user_id in settings.allowed_telegram_ids


@dp.message(CommandStart())
async def start(message: Message) -> None:
    if not message.from_user or not _allowed(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть панель", web_app=WebAppInfo(url=settings.mini_app_url))]]
    )
    await message.answer(
        "Управление серверами 3x-ui.\n\n"
        "Команды: /servers, /status <id>, /logs <id> [строки], "
        "/updates <id>, /ssh <id> <команда>.",
        reply_markup=keyboard,
    )


def _server(server_id: str):
    return next((item for item in settings.servers if item.id == server_id), None)


async def _authorized_message(message: Message) -> bool:
    if not message.from_user or not _allowed(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return False
    return True


async def _send_output(message: Message, heading: str, output: str) -> None:
    value = (output or "Команда завершилась без текстового вывода.").strip()
    value = value[-settings.bot_output_max_chars:]
    chunks = [value[index:index + 3500] for index in range(0, len(value), 3500)] or [value]
    await message.answer(heading)
    for chunk in chunks:
        await message.answer(chunk)


@dp.message(Command("servers"))
async def servers_command(message: Message) -> None:
    if not await _authorized_message(message):
        return
    lines = [f"{item.id} — {item.name} ({item.location or 'без локации'})" for item in settings.servers]
    await message.answer("Серверы:\n" + "\n".join(lines))


@dp.message(Command("status"))
async def status_command(message: Message) -> None:
    if not await _authorized_message(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    server = _server(parts[1].strip()) if len(parts) > 1 else None
    if not server:
        await message.answer("Использование: /status <server_id>")
        return
    try:
        status = await SSHService(server).status()
        await message.answer(
            f"{server.name}\n"
            f"x-ui: {status['xui_service']} {status['xui_version']}\n"
            f"Uptime: {status['uptime_seconds']} сек.\n"
            f"Load: {status['load']['one']}, {status['load']['five']}, {status['load']['fifteen']}\n"
            f"Disk: {status['disk']['percent']}%"
        )
    except Exception as exc:
        await message.answer(f"Ошибка SSH: {str(exc)[:1000]}")


@dp.message(Command("logs"))
async def logs_command(message: Message) -> None:
    if not await _authorized_message(message):
        return
    parts = (message.text or "").split()
    server = _server(parts[1]) if len(parts) > 1 else None
    if not server:
        await message.answer("Использование: /logs <server_id> [10-500]")
        return
    try:
        lines = int(parts[2]) if len(parts) > 2 else 100
        output = await SSHService(server).xui_logs(lines)
        await _send_output(message, f"Последние записи x-ui на {server.name}:", output)
    except Exception as exc:
        await message.answer(f"Ошибка: {str(exc)[:1000]}")


@dp.message(Command("updates"))
async def updates_command(message: Message) -> None:
    if not await _authorized_message(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    server = _server(parts[1].strip()) if len(parts) > 1 else None
    if not server:
        await message.answer("Использование: /updates <server_id>")
        return
    try:
        output = await SSHService(server).upgradable_packages()
        await _send_output(message, f"Доступные обновления на {server.name}:", output)
    except Exception as exc:
        await message.answer(f"Ошибка SSH: {str(exc)[:1000]}")


@dp.message(Command("ssh"))
async def raw_ssh_command(message: Message) -> None:
    if not await _authorized_message(message):
        return
    parts = (message.text or "").split(maxsplit=2)
    server = _server(parts[1]) if len(parts) > 1 else None
    if not server or len(parts) < 3:
        await message.answer("Использование: /ssh <server_id> <команда>")
        return
    command = parts[2]
    try:
        result = await SSHService(server).run_raw(command)
        telegram_user = TelegramUser(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        await write_audit(telegram_user, "raw_ssh", server.id, {
            "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
            "exit_status": result.exit_status,
        })
        output = result.stdout
        if result.stderr:
            output += ("\nSTDERR:\n" if output else "STDERR:\n") + result.stderr
        await _send_output(message, f"{server.name}: exit {result.exit_status}", output)
    except Exception as exc:
        await message.answer(f"Ошибка SSH: {str(exc)[:1000]}")


@dp.message(F.text)
async def fallback(message: Message) -> None:
    if message.from_user and _allowed(message.from_user.id):
        await message.answer("Откройте Mini App кнопкой меню.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = settings.bot_token.get_secret_value()
    if token == "change-me":
        raise RuntimeError("BOT_TOKEN is not configured")
    bot = Bot(token=token)
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Серверы", web_app=WebAppInfo(url=settings.mini_app_url)))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
