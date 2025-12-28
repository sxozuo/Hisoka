"""
    📋 PastebinUploader - Публикация и скачивание текста с Pastebin
"""

__version__ = (1, 3, 0)

# meta developer: @sxozuo
# requires: aiohttp

import aiohttp
import logging
from typing import Optional
from io import BytesIO

from .. import loader, utils
from herokutl.types import Message

logger = logging.getLogger(__name__)

PASTEBIN_POST_URL = "https://pastebin.com/api/api_post.php"
PASTEBIN_RAW_URL = "https://pastebin.com/raw/{}"


@loader.tds
class PastebinUploader(loader.Module):
    """Публикация и загрузка текста Pastebin"""
    
    strings = {
        "name": "PastebinUploader",
        "no_api_key": "❌ <b>Ошибка:</b> API ключ Pastebin не указан в конфигурации.",
        "no_content": "❌ <b>Ошибка:</b> Укажите текст или ответьте на сообщение с текстом.",
        "processing": "⏳ Публикация на Pastebin...",
        "success": "✅ <b>Успешно:</b> Ваша запись опубликована:\n{}",
        "api_error": "❌ <b>Ошибка API:</b> Не удалось опубликовать запись. Ответ: {}",
        "http_error": "❌ <b>Ошибка HTTP:</b> Проблема с подключением: {}",
        "fetching": "⏳ Скачиваю текст с Pastebin...",
        "invalid_link": "❌ <b>Ошибка:</b> Укажите корректную ссылку на пасту или только ее ключ.",
        "fetch_success": "✅ <b>Успешно:</b> Текст загружен и отправлен файлом <code>{}.txt</code>",
        "fetch_failed": "❌ <b>Ошибка:</b> Не удалось загрузить пасту. Сервер вернул ошибку, возможно, паста удалена или приватна.",
        "wiki_guide": (
            "🔑 <b>ГАЙД: Как получить DEV API Key для Pastebin</b>\n\n"
            "Для работы команды <code>.paste</code> необходим <b>DEV API Key</b>. Это бесплатно.\n\n"
            "<b>Шаг 1. Регистрация и Вход</b>\n"
            "Перейдите на <a href=\"https://pastebin.com/signup\">Pastebin.com</a> и зарегистрируйтесь (или войдите в существующий аккаунт).\n\n"
            "<b>Шаг 2. Получение Ключа</b>\n"
            "1. Перейдите по прямой ссылке на страницу API: <a href=\"https://pastebin.com/api\">Pastebin API</a>.\n"
            "2. Прокрутите страницу до раздела <b>'Your unique Dev API Key is'</b>.\n"
            "3. Скопируйте длинный буквенно-цифровой ключ, который находится под этим заголовком.\n\n"
            "<b>Шаг 3. Настройка Модуля</b>\n"
            "Вставьте скопированный ключ в конфигурацию модуля <b>PastebinUploader</b> в настройках бота:\n"
            "⚙️ <code>.config PastebinUploader</code> → <code>api_dev_key</code>.\n\n"
            "Готово! Теперь команда <code>.paste</code> будет работать."
        ),
    }
    
    strings_ru = {
        "no_api_key": "❌ <b>Ошибка:</b> API ключ Pastebin не указан в конфигурации.",
        "no_content": "❌ <b>Ошибка:</b> Укажите текст или ответьте на сообщение с текстом.",
        "processing": "⏳ Публикация на Pastebin...",
        "success": "✅ <b>Успешно:</b> Ваша запись опубликована:\n{}",
        "api_error": "❌ <b>Ошибка API:</b> Не удалось опубликовать запись. Ответ: {}",
        "http_error": "❌ <b>Ошибка HTTP:</b> Проблема с подключением: {}",
        "fetching": "⏳ Скачиваю текст с Pastebin...",
        "invalid_link": "❌ <b>Ошибка:</b> Укажите корректную ссылку на пасту или только ее ключ.",
        "fetch_success": "✅ <b>Успешно:</b> Текст загружен и отправлен файлом <code>{}.txt</code>",
        "fetch_failed": "❌ <b>Ошибка:</b> Не удалось загрузить пасту. Сервер вернул ошибку, возможно, паста удалена или приватна.",
        "wiki_guide": (
            "🔑 <b>ГАЙД: Как получить DEV API Key для Pastebin</b>\n\n"
            "Для работы команды <code>.paste</code> необходим <b>DEV API Key</b>. Это бесплатно.\n\n"
            "<b>Шаг 1. Регистрация и Вход</b>\n"
            "Перейдите на <a href=\"https://pastebin.com/signup\">Pastebin.com</a> и зарегистрируйтесь (или войдите в существующий аккаунт).\n\n"
            "<b>Шаг 2. Получение Ключа</b>\n"
            "1. Перейдите по прямой ссылке на страницу API: <a href=\"https://pastebin.com/api\">Pastebin API</a>.\n"
            "2. Прокрутите страницу до раздела <b>'Your unique Dev API Key is'</b>.\n"
            "3. Скопируйте длинный буквенно-цифровой ключ, который находится под этим заголовком.\n\n"
            "<b>Шаг 3. Настройка Модуля</b>\n"
            "Вставьте скопированный ключ в конфигурацию модуля <b>PastebinUploader</b> в настройках бота:\n"
            "⚙️ <code>.config PastebinUploader</code> → <code>api_dev_key</code>.\n\n"
            "Готово! Теперь команда <code>.paste</code> будет работать."
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_dev_key",
                "",
                "DEV API Key Pastebin (обязательно для .paste)",
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                "paste_expire_date",
                "1D",
                "Срок хранения записи (N, 10M, 1H, 1D, 1W, 2W, 1M, 6M, 1Y)",
                validator=loader.validators.Choice(["N", "10M", "1H", "1D", "1W", "2W", "1M", "6M", "1Y"])
            ),
            loader.ConfigValue(
                "paste_format",
                "text",
                "Подсветка синтаксиса (например: python, sql, text, json)",
                validator=loader.validators.String()
            ),
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.get("timeout", 30))
        )

    async def on_unload(self):
        if self.session:
            await self.session.close()

    async def _create_paste(self, content: str, title: str = "") -> str:
        data = {
            "api_dev_key": self.config["api_dev_key"],
            "api_option": "paste",
            "api_paste_code": content,
            "api_paste_name": title,
            "api_paste_format": self.config["paste_format"],
            "api_paste_expire_date": self.config["paste_expire_date"],
        }
        
        try:
            async with self.session.post(PASTEBIN_POST_URL, data=data) as response:
                response.raise_for_status()
                paste_url = await response.text()
                
                if paste_url.startswith("Bad API request"):
                    raise ValueError(paste_url)
                
                return paste_url
        
        except aiohttp.ClientResponseError as e:
            logger.exception(f"HTTP Error: {e.status}")
            raise ConnectionError(f"HTTP Error {e.status}: {e.message}")
        except aiohttp.ClientError as e:
            logger.exception(f"Connection Error: {e}")
            raise ConnectionError(f"Connection error: {e}")
        except ValueError as e:
            logger.error(f"Pastebin API Error: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in _create_paste: {e}")
            raise RuntimeError(f"Unexpected error: {e}")

    @loader.command(
        ru_doc="[заголовок] <текст> - Опубликовать текст на Pastebin. Если текст не указан, использует ответ на сообщение.",
        en_doc="[title] <text> - Publish text to Pastebin. If no text, uses the replied message."
    )
    async def pastecmd(self, message: Message):
        """Создает новую пасту на Pastebin из текста или ответа на сообщение."""
        if not self.config["api_dev_key"]:
            await utils.answer(message, self.strings("no_api_key"))
            return
        
        args = utils.get_args_raw(message).split(maxsplit=1)
        content = None
        title = ""
        
        if len(args) == 2:
            title = utils.escape_html(args[0])
            content = args[1]
        elif len(args) == 1:
            content = args[0]
        
        if not content:
            reply = await message.get_reply_message()
            if reply and reply.text:
                content = reply.text
                if len(args) == 1:
                    title = utils.escape_html(args[0])
        
        if not content or content.strip() == "":
            await utils.answer(message, self.strings("no_content"))
            return
        
        await utils.answer(message, self.strings("processing"))
        
        try:
            paste_url = await self._create_paste(content, title)
            await utils.answer(
                message,
                self.strings("success").format(paste_url)
            )
        except ConnectionError as e:
            await utils.answer(message, self.strings("http_error").format(utils.escape_html(str(e))))
        except (ValueError, RuntimeError) as e:
            await utils.answer(message, self.strings("api_error").format(utils.escape_html(str(e))))
        except Exception as e:
            logger.exception(f"Error in pastecmd: {e}")
            await utils.answer(message, self.strings("api_error").format(utils.escape_html(str(e))))


    @loader.command(
        ru_doc="<ключ/ссылка> - Скачать текст из Pastebin по ключу или ссылке и отправить файлом.",
        en_doc="<key/link> - Download text from Pastebin by key or link and send as a file."
    )
    async def gpastecmd(self, message: Message):
        """Скачивает содержимое пасты по ключу/ссылке и отправляет его файлом."""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, self.strings("invalid_link"))
            return
        
        paste_key = args.split('/')[-1].split('?')[0].strip()
        
        if not paste_key or len(paste_key) < 5:
            await utils.answer(message, self.strings("invalid_link"))
            return

        await utils.answer(message, self.strings("fetching"))
        
        download_url = PASTEBIN_RAW_URL.format(paste_key)

        try:
            async with self.session.get(download_url) as response:
                if response.status != 200:
                    raise ConnectionError(f"HTTP Status: {response.status}")

                content_bytes = await response.read()
                content = content_bytes.decode('utf-8', errors='ignore')
                
                if "Page not found" in content or "private" in content:
                    await utils.answer(message, self.strings("fetch_failed"))
                    return
                
            file_to_send = BytesIO(content_bytes)
            file_to_send.name = f"pastebin_{paste_key}.txt"

            await self._client.send_file(
                message.chat_id,
                file_to_send,
                caption=self.strings("fetch_success").format(paste_key),
                reply_to=message.reply_to_msg_id or message.id
            )
            await message.delete()

        except (aiohttp.ClientError, ConnectionError) as e:
            logger.exception(f"Error fetching paste: {e}")
            await utils.answer(message, self.strings("http_error").format(utils.escape_html(str(e))))
        except Exception as e:
            logger.exception(f"Unexpected error in gpastecmd: {e}")
            await utils.answer(message, self.strings("api_error").format(utils.escape_html(str(e))))

    @loader.command(
        ru_doc="Показать гайд по получению DEV API Key для Pastebin.",
        en_doc="Show guide on how to get DEV API Key for Pastebin."
    )
    async def wkcmd(self, message: Message):
        """Показывает подробный гайд о том, как получить DEV API Key для Pastebin."""
        
        await utils.answer(message, self.strings("wiki_guide"))