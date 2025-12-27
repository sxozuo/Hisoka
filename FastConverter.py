"""
    ⚡ FastConverter - Конвертер файлов
    
    Модуль для двусторонней конвертации между текстовыми файлами и PY, CPP, MD, JS.
"""

__version__ = (3, 0, 0) # Мажорное обновление: двусторонняя конвертация

# meta developer: @sxozuo 
# scope: hikka_only
# requires: 

import logging
import io
import os
from .. import loader, utils
from herokutl.types import Message 

logger = logging.getLogger(__name__)


@loader.tds
class FastConverter(loader.Module):
    """Конвертер файлов TXT ↔ PY, CPP, MD, JS"""
    
    # Список всех разрешенных расширений
    ALLOWED_EXTENSIONS = ["txt", "py", "cpp", "md", "js"]
    
    strings = {
        "name": "FastConverter",
        "no_reply": "❌ <b>Ошибка:</b> Необходимо ответить на сообщение, содержащее файл.",
        "no_document": "❌ <b>Ошибка:</b> Прикрепленный объект не является документом.",
        "not_allowed_ext": "❌ <b>Ошибка:</b> Поддерживаются только: <code>py, cpp, js, md, txt</code>.",
        "processing": "⚙️ Конвертация файла: <code>{}</code> -> <code>{}</code>...",
        "success": "✅ Файл успешно сконвертирован: <code>{}</code>.",
        "file_too_large": "❌ <b>Ошибка:</b> Файл слишком большой для обработки (лимит 5 МБ).",
        "no_ext": "❌ <b>Ошибка:</b> Укажите целевое расширение. Доступные: <code>py, cpp, md, js, txt</code>.",
        "bad_ext": "❌ <b>Ошибка:</b> Недопустимое расширение <code>{}</code>. Доступные: <code>py, cpp, md, js, txt</code>.",
        "same_ext": "❌ <b>Ошибка:</b> Исходное расширение <code>{}</code> совпадает с целевым.",
    }
    
    strings_ru = {
        "no_reply": "❌ <b>Ошибка:</b> Необходимо ответить на сообщение, содержащее файл.",
        "no_document": "❌ <b>Ошибка:</b> Прикрепленный объект не является документом.",
        "not_allowed_ext": "❌ <b>Ошибка:</b> Поддерживаются только: <code>py, cpp, js, md, txt</code>.",
        "processing": "⚙️ Конвертация файла: <code>{}</code> -> <code>{}</code>...",
        "success": "✅ Файл успешно сконвертирован: <code>{}</code>.",
        "file_too_large": "❌ <b>Ошибка:</b> Файл слишком большой для обработки (лимит 5 МБ).",
        "no_ext": "❌ <b>Ошибка:</b> Укажите целевое расширение. Доступные: <code>py, cpp, md, js, txt</code>.",
        "bad_ext": "❌ <b>Ошибка:</b> Недопустимое расширение <code>{}</code>. Доступные: <code>py, cpp, md, js, txt</code>.",
        "same_ext": "❌ <b>Ошибка:</b> Исходное расширение <code>{}</code> совпадает с целевым.",
        "_cls_doc": "Конвертер файлов TXT ↔ PY, CPP, MD, JS",
        "_cmd_tocmd_doc": "<расширение> - конвертирует прикрепленный файл в указанное расширение (py, cpp, md, js, txt).",
    }

    def __init__(self):
        self.config = loader.ModuleConfig()

    async def _convert_and_send(self, message: Message, target_ext: str):
        """Общая логика конвертации и отправки."""
        
        reply = await message.get_reply_message()
        
        if not reply:
            await utils.answer(message, self.strings("no_reply"))
            return

        if not reply.document:
            await utils.answer(message, self.strings("no_document"))
            return
            
        file_name = reply.document.attributes[0].file_name if reply.document.attributes else ""
        
        # 1. Получение текущего расширения и проверка на соответствие
        base_name, current_ext = os.path.splitext(file_name)
        
        if not current_ext:
             # Если у файла нет расширения, используем "bin" для дальнейшей проверки
            current_ext = "" 
            current_ext_clean = "NONE"
        else:
            current_ext_clean = current_ext[1:].lower() # Убираем точку и приводим к нижнему регистру
            
        
        if current_ext_clean not in self.ALLOWED_EXTENSIONS:
            await utils.answer(message, self.strings("not_allowed_ext"))
            return
            
        # 2. Проверка, не пытается ли пользователь конвертировать в то же самое расширение
        if current_ext_clean == target_ext:
            await utils.answer(message, self.strings("same_ext").format(current_ext))
            return

        if reply.document.size > 5 * 1024 * 1024: 
            await utils.answer(message, self.strings("file_too_large"))
            return

        # 3. Подготовка нового имени файла
        if current_ext_clean == "none":
            new_file_name = f"{file_name}.{target_ext}"
        else:
            new_file_name = f"{base_name}.{target_ext}"
        
        status_message = await utils.answer(
            message, 
            self.strings("processing").format(current_ext_clean.upper() if current_ext_clean else "File", target_ext.upper())
        )
        
        try:
            # 4. Скачивание и отправка с новым именем
            file_bytes = await reply.download_media(bytes)
            
            output_file = io.BytesIO(file_bytes)
            output_file.name = new_file_name

            await message.client.send_file(
                utils.get_chat_id(message),
                output_file,
                caption=self.strings("success").format(new_file_name),
                reply_to=reply
            )
            await status_message.delete()
            
        except Exception as e:
            logger.exception(f"File conversion error: {e}")
            await utils.answer(status_message, self.strings("error").format(str(e)))


    @loader.command(aliases=["to"])
    async def tocmd(self, message: Message):
        """Конвертирует прикрепленный файл в указанное расширение (py, cpp, md, js, txt)."""
        
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_ext"))
            return
            
        target_ext = args.lower().strip()
        
        if target_ext not in self.ALLOWED_EXTENSIONS:
            await utils.answer(message, self.strings("bad_ext").format(target_ext))
            return

        await self._convert_and_send(message, target_ext)