"""
    🖼️ XenoAI - Мощный модуль для генерации изображений.
    
    Модуль для создания изображений с использованием нейросетей Runware.ai.
"""

__version__ = (1, 0, 3) # Обновление версии

# meta developer: @sxozuo 
# scope: hikka_only
# requires: aiohttp

import logging
import uuid
import aiohttp
from .. import loader, utils
from herokutl.types import Message 

logger = logging.getLogger(__name__)


@loader.tds
class XenoAI(loader.Module):
    """Генерация Изображения☃""" # <-- Изменено здесь
    
    strings = {
        "name": "XenoAI",
        "no_args": "❌ <b>Error:</b> Prompt is required\nUsage: <code>.xeno <prompt></code>",
        "processing": "🎨 <b>Generating image...</b>\nPrompt: <i>{}</i>",
        "uploading": "📤 <b>Uploading...</b>",
        "success": "✅ <b>Image generated!</b>\nTime: <code>{:.2f}s</code>",
        "error": "❌ <b>API Error:</b> {}",
        "net_error": "❌ <b>Network Error:</b> {}",
    }
    
    strings_ru = {
        "no_args": "❌ <b>Ошибка:</b> Не указан запрос\nИспользование: <code>.xeno <промпт></code>",
        "processing": "Генерация изображения☃",
        "uploading": "📤 <b>Загрузка...</b>",
        "success": "✅ <b>Изображение готово!</b>", 
        "error": "❌ <b>Ошибка API:</b> {}",
        "net_error": "❌ <b>Ошибка сети:</b> {}",
        "_cls_doc": "Генерация Изображения☃", # <-- Изменено здесь
        "_cmd_xenocmd_doc": "<промпт> - сгенерировать изображение"
    }

    def __init__(self):
        """Конфигурация модуля"""
        self.API_KEY = "hrxmLmmDUFfgHTbRsqoc4b3DWTbLYvfi"
        
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "model",
                "runware:100@1",
                "Model ID to use",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "width",
                512,
                "Image width",
                validator=loader.validators.Integer(minimum=64, maximum=2048)
            ),
            loader.ConfigValue(
                "height",
                512,
                "Image height",
                validator=loader.validators.Integer(minimum=64, maximum=2048)
            ),
        )

    async def client_ready(self, client, db):
        """Инициализация сессии"""
        self._client = client
        self._db = db
        # Создаем сессию с таймаутом
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Heroku UserBot/XenoAIMod"},
            timeout=aiohttp.ClientTimeout(total=60)
        )

    async def on_unload(self):
        """Закрытие сессии при выгрузке"""
        if hasattr(self, "session"):
            await self.session.close()

    @loader.command(
        ru_doc="<промпт> - сгенерировать изображение",
        en_doc="<prompt> - generate image",
        aliases=["xeno"]
    )
    async def xenocmd(self, message: Message):
        """Generate image using Runware API"""
        
        prompt = utils.get_args_raw(message)
        
        if not prompt:
            await utils.answer(message, self.strings("no_args"))
            return

        # 1. Показываем процесс: "Генерация изображения☃"
        status_message = await utils.answer(
            message, 
            self.strings("processing").format(utils.escape_html(prompt))
        )
        
        # 2. Подготовка данных
        payload = [{
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "positivePrompt": prompt,
            "model": self.config["model"],
            "width": self.config["width"],
            "height": self.config["height"],
            "numberResults": 1
        }]

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        # 3. Выполнение запроса
        try:
            async with self.session.post(
                "https://api.runware.ai/v1",
                json=payload,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    # Попытка получить ошибку из JSON, если не удалось, берем сырой текст
                    try:
                        error_data = await response.json()
                        error_text = error_data.get('detail', error_data.get('error', f"HTTP {response.status}"))
                    except json.JSONDecodeError:
                        error_text = f"HTTP {response.status} - {await response.text()[:100]}..."

                    await utils.answer(status_message, self.strings("error").format(error_text))
                    return

                data = await response.json()
                
                # Парсинг ответа
                if "data" in data and len(data["data"]) > 0:
                    image_url = data["data"][0].get("imageURL")
                    if not image_url:
                        await utils.answer(status_message, self.strings("error").format("No image URL in response"))
                        return
                    
                    # 4. Загрузка и отправка
                    await utils.answer(status_message, self.strings("uploading"))
                    
                    await message.client.send_file(
                        utils.get_chat_id(message),
                        image_url,
                        caption=f"🎨 <b>Xeno AI</b>\nRequest: <code>{utils.escape_html(prompt)}</code>",
                        reply_to=message.reply_to_msg_id
                    )
                    await status_message.delete()
                
                else:
                    await utils.answer(
                        status_message, 
                        self.strings("error").format(f"Invalid response: {data}")
                    )

        except aiohttp.ClientError as e:
            await utils.answer(status_message, self.strings("net_error").format(str(e)))
        except Exception as e:
            logger.exception(f"Xeno AI Error: {e}")
            await utils.answer(status_message, self.strings("error").format(str(e)))