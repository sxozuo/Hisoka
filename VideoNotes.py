"""
    🎥 VideoNotes - Конвертирует видео в кружочек

    Ответь на видео командой .vn — отправит как video note (кружочек).
    Требует ffmpeg на сервере.
"""

version = (1, 0, 0)

# meta developer: @xyecoder
# meta banner: https://files.catbox.moe/2s9dvz.jpg
# scope: hikka_only
# requires: ffmpeg-python

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
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


@loader.tds
class VideoNotesMod(loader.Module):
    """Конвертирует видео в кружочек"""

    version = (1, 0, 0)

    strings = {
        "name": "VideoNotes",
        "no_reply": "❌ Ответь на видео или гифку.",
        "processing": "⏳ Конвертирую в кружочек...",
        "no_ffmpeg": "❌ ffmpeg не установлен на сервере.",
        "error": "❌ Ошибка: <code>{}</code>",
        "too_big": "❌ Видео слишком большое. Максимум — <code>{}MB</code>",
    }

    strings_ru = {
        "no_reply": "❌ Ответь на видео или гифку.",
        "processing": "⏳ Конвертирую в кружочек...",
        "no_ffmpeg": "❌ ffmpeg не установлен на сервере.",
        "error": "❌ Ошибка: <code>{}</code>",
        "too_big": "❌ Видео слишком большое. Максимум — <code>{}MB</code>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "max_size_mb",
                50,
                "",
                validator=loader.validators.Integer(minimum=1, maximum=200),
            ),
        )

    async def client_ready(self, client, db):
        self._client = client

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def _convert(self, input_path: str, output_path: str) -> bool:
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=384:384",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "28",
                "-c:a", "aac",
                "-t", "60",
                output_path
            ], capture_output=True, check=True)
            return True
        except Exception as e:
            logger.exception(e)
            return False

    @loader.command(
        ru_doc="— конвертировать видео в кружочек (ответь на видео)",
        en_doc="— convert video to video note (reply to video)",
    )
    async def vn(self, message: Message):
        reply = await message.get_reply_message()

        if not reply or not reply.video and not reply.gif and not reply.document:
            await utils.answer(message, self.strings("no_reply"))
            return

        if not self._check_ffmpeg():
            await utils.answer(message, self.strings("no_ffmpeg"))
            return

        doc = reply.video or reply.gif or reply.document
        max_bytes = self.config["max_size_mb"] * 1024 * 1024
        if doc.size > max_bytes:
            await utils.answer(message, self.strings("too_big").format(self.config["max_size_mb"]))
            return

        await utils.answer(message, self.strings("processing"))

        with tempfile.TemporaryDirectory() as tmp:
            input_path = os.path.join(tmp, "input.mp4")
            output_path = os.path.join(tmp, "output.mp4")

            try:
                await reply.download_media(input_path)
            except Exception as e:
                logger.exception(e)
                await utils.answer(message, self.strings("error").format(utils.escape_html(str(e))))
                return

            if not self._convert(input_path, output_path):
                await utils.answer(message, self.strings("error").format("ffmpeg conversion failed"))
                return

            try:
                await self._client.send_file(
                    message.chat_id,
                    output_path,
                    video_note=True,
                )
                await message.delete()
            except Exception as e:
                logger.exception(e)
                await utils.answer(message, self.strings("error").format(utils.escape_html(str(e))))
