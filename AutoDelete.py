"""
    🗑 AutoDelete - Автоудаление сообщений

    Автоматически удаляет все сообщения в чате через заданное время.
    Глобальный таймер для всех сообщений.
"""

version = (1, 0, 0)

# meta developer: @xyecoder
# meta banner: https://files.catbox.moe/2s9dvz.jpg
# scope: hikka_only
# ██╗  ██╗██╗███████╗ ██████╗ ██╗  ██╗ █████╗
# ██║  ██║██║██╔════╝██╔═══██╗██║ ██╔╝██╔══██╗
# ███████║██║███████╗██║   ██║█████╔╝ ███████║
# ██╔══██║██║╚════██║██║   ██║██╔═██╗ ██╔══██║
# ██║  ██║██║███████║╚██████╔╝██║  ██╗██║  ██║
# ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
# © 2026 @xyecoder | All rights reserved
# ⛔ Копирование без разрешения запрещено


from .. import loader, utils
from herokutl.types import Message
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


def _parse_time(s: str) -> int:
    s = s.strip().lower()
    if s.endswith("s"):
        return int(s[:-1])
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("d"):
        return int(s[:-1]) * 86400
    return int(s)


@loader.tds
class AutoDeleteMod(loader.Module):
    """Автоудаление всех сообщений в чате"""

    version = (1, 0, 0)

    strings = {
        "name": "AutoDelete",
        "enabled": "🗑 <b>AutoDelete включён.</b>\nУдаляю все сообщения через <code>{}</code>",
        "disabled": "✅ <b>AutoDelete выключен.</b>",
        "already_off": "❌ <b>AutoDelete уже выключен.</b>",
        "already_on": "⚠️ <b>AutoDelete уже включён.</b> Задержка: <code>{}</code>\nЧтобы выключить: <code>.adoff</code>",
        "invalid": "❌ Неверный формат. Примеры: <code>30s</code>, <code>5m</code>, <code>2h</code>, <code>1d</code>",
        "no_args": "❌ Укажи время: <code>.adon 5m</code>",
        "status_on": "📊 <b>AutoDelete включён.</b>\nЗадержка: <code>{}</code>\nУдалено за сессию: <code>{}</code>",
        "status_off": "📊 <b>AutoDelete выключен.</b>",
    }

    strings_ru = {
        "enabled": "🗑 <b>AutoDelete включён.</b>\nУдаляю все сообщения через <code>{}</code>",
        "disabled": "✅ <b>AutoDelete выключен.</b>",
        "already_off": "❌ <b>AutoDelete уже выключен.</b>",
        "already_on": "⚠️ <b>AutoDelete уже включён.</b> Задержка: <code>{}</code>\nЧтобы выключить: <code>.adoff</code>",
        "invalid": "❌ Неверный формат. Примеры: <code>30s</code>, <code>5m</code>, <code>2h</code>, <code>1d</code>",
        "no_args": "❌ Укажи время: <code>.adon 5m</code>",
        "status_on": "📊 <b>AutoDelete включён.</b>\nЗадержка: <code>{}</code>\nУдалено за сессию: <code>{}</code>",
        "status_off": "📊 <b>AutoDelete выключен.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "delay",
                0,
                "",
                validator=loader.validators.Integer(minimum=0),
            ),
        )
        self._deleted = 0

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._deleted = 0

    def _fmt(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}с"
        if seconds < 3600:
            return f"{seconds // 60}м"
        if seconds < 86400:
            return f"{seconds // 3600}ч"
        return f"{seconds // 86400}д"

    async def _schedule_delete(self, message: Message, delay: int):
        await asyncio.sleep(delay)
        try:
            await message.delete()
            self._deleted += 1
        except Exception as e:
            logger.exception(e)

    @loader.watcher(only_messages=True)
    async def watcher(self, message: Message):
        delay = self.config["delay"]
        if delay <= 0:
            return
        asyncio.ensure_future(self._schedule_delete(message, delay))

    @loader.command(
        ru_doc="<время> — включить автоудаление (30s / 5m / 2h / 1d)",
        en_doc="<time> — enable auto delete (30s / 5m / 2h / 1d)",
    )
    async def adon(self, message: Message):
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        if self.config["delay"] > 0:
            await utils.answer(message, self.strings("already_on").format(self._fmt(self.config["delay"])))
            return

        try:
            seconds = _parse_time(args)
            if seconds <= 0:
                raise ValueError
        except Exception:
            await utils.answer(message, self.strings("invalid"))
            return

        self.config["delay"] = seconds
        await utils.answer(message, self.strings("enabled").format(self._fmt(seconds)))

    @loader.command(
        ru_doc="— выключить автоудаление",
        en_doc="— disable auto delete",
    )
    async def adoff(self, message: Message):
        if self.config["delay"] <= 0:
            await utils.answer(message, self.strings("already_off"))
            return

        self.config["delay"] = 0
        await utils.answer(message, self.strings("disabled"))

    @loader.command(
        ru_doc="— статус автоудаления",
        en_doc="— auto delete status",
    )
    async def adstatus(self, message: Message):
        delay = self.config["delay"]
        if delay <= 0:
            await utils.answer(message, self.strings("status_off"))
        else:
            await utils.answer(message, self.strings("status_on").format(self._fmt(delay), self._deleted))
