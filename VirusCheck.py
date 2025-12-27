"""
    🛡️ VirusCheck — VirusTotal & Code Inspector
    
    Продвинутый модуль для сканирования файлов через VirusTotal, 
    эвристического анализа кода и безопасного просмотра .py файлов.
"""

__version__ = (5, 1, 1)

# meta developer: @sxozuo @HarutyaModules
# meta pic: https://img.icons8.com/fluency/160/security-checked.png
# scope: hikka_only
# requires: aiohttp

import asyncio
import logging
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
from herokutl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    (r"os\.(system|popen|spawn|exec)", "OS Command Execution"),
    (r"subprocess\.(run|call|Popen)", "Subprocess Execution"),
    (r"eval\(", "Code Evaluation (eval)"),
    (r"exec\(", "Code Execution (exec)"),
    (r"__import__\(", "Dynamic Import"),
    (r"base64\.b64decode\(", "Obfuscation (Base64)"),
    (r"shutil\.rmtree\(", "File Deletion (rmtree)"),
    (r"getattr\(", "Dynamic Attribute Access"),
    (r"requests\.", "Network Activity (requests)"),
    (r"aiohttp\.", "Network Activity (aiohttp)"),
]

@loader.tds
class VirusCheckMod(loader.Module):
    """VirusTotal scans and safe .py code viewer"""

    strings = {
        "name": "VirusCheck",
        "processing": "⏳ <b>Обработка...</b>",
        
        # Code Viewer
        "no_file": "❌ <b>Файл не найден в ответе!</b>",
        "too_large": "❌ <b>Файл слишком большой!</b> (макс. {} KB)",
        "code_title": "💻 <b>Файл:</b> <code>{}</code>\n📄 <b>Страница:</b> <code>{}/{}</code>",
        "session_expired": "❌ <b>Сессия истекла.</b> Отправьте команду заново.",
        
        # VirusTotal
        "no_key": "❌ <b>API ключ VirusTotal не установлен!</b> Используйте <code>.vtkey <key></code>",
        "key_saved": "✅ <b>API ключ сохранен!</b>",
        "scan_start": "🚀 <b>Запуск анализа...</b>",
        "uploading": "📤 <b>Загрузка на VirusTotal...</b>",
        "vt_report": (
            "🔬 <b>Отчет VirusTotal</b>\n\n"
            "🔗 <a href='{link}'>Открыть отчет</a>\n"
            "🔍 <b>Результат:</b> {malicious}/{total} ({status})\n"
            "🕒 <b>Дата:</b> <code>{date}</code>"
        ),
        "clean": "Чисто ✅",
        "danger": "Опасно 🚨",
        
        # Heuristics
        "h_title": "🛡️ <b>Эвристический анализ:</b>",
        "h_clean": "✅ Подозрительных паттернов не обнаружено.",
        "h_warning": "⚠️ <b>Найдены подозрительные элементы:</b>",
        
        # Config
        "cfg_key": "API ключ VirusTotal",
        "cfg_max_kb": "Макс. размер файла (KB)",
        "cfg_cooldown": "Задержка (сек)",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("vt_api_key", "", lambda: self.strings("cfg_key"), validator=loader.validators.Hidden()),
            loader.ConfigValue("max_code_kb", 512, lambda: self.strings("cfg_max_kb"), validator=loader.validators.Integer(minimum=10)),
            loader.ConfigValue("cooldown", 5, lambda: self.strings("cfg_cooldown"), validator=loader.validators.Integer(minimum=0)),
        )
        self._sessions = {}
        self._last_scan = 0

    async def client_ready(self, client, db):
        self._client = client
        self._http = aiohttp.ClientSession(
            headers={"x-apikey": self.config["vt_api_key"]} if self.config["vt_api_key"] else {}
        )

    async def on_unload(self):
        await self._http.close()

    def _get_heuristics(self, code: str) -> List[str]:
        found = []
        for pattern, desc in DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                found.append(f"• <code>{desc}</code>")
        return found

    @loader.command(ru_doc="<ключ> - Установить API ключ VirusTotal")
    async def vtkeycmd(self, message: Message):
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Введите ключ!")
            return
        self.config["vt_api_key"] = args
        self._http._default_headers.update({"x-apikey": args})
        await utils.answer(message, self.strings("key_saved"))

    @loader.command(ru_doc="Проверить файл в ответе через VirusTotal")
    async def scanfilecmd(self, message: Message):
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_file"))
            return

        if not self.config["vt_api_key"]:
            await utils.answer(message, self.strings("no_key"))
            return

        if time.time() - self._last_scan < self.config["cooldown"]:
            await utils.answer(message, f"⏳ Подождите {self.config['cooldown']} сек.")
            return

        msg = await utils.answer(message, self.strings("uploading"))
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
                path = tmp.name
                await self._client.download_media(reply, path)
            
            heuristics = ""
            if reply.file and reply.file.name and reply.file.name.endswith(".py"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    found = self._get_heuristics(f.read())
                    heuristics = f"\n\n{self.strings('h_title')}\n" + ("\n".join(found) if found else self.strings("h_clean"))

            form = aiohttp.FormData()
            form.add_field("file", open(path, "rb"), filename=reply.file.name or "file.bin")
            
            async with self._http.post("https://www.virustotal.com/api/v3/files", data=form) as resp:
                if resp.status != 200:
                    err = await resp.json()
                    await utils.answer(msg, f"❌ VT Error: {err.get('error', {}).get('message')}")
                    return
                data = await resp.json()
            
            analysis_id = data["data"]["id"]
            await utils.answer(msg, self.strings("scan_start") + heuristics)
            
            for _ in range(12):
                await asyncio.sleep(10)
                async with self._http.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}") as resp:
                    res = await resp.json()
                    if res["data"]["attributes"]["status"] == "completed":
                        stats = res["data"]["attributes"]["stats"]
                        malicious = stats["malicious"] + stats["suspicious"]
                        total = sum(stats.values())
                        report_link = f"https://www.virustotal.com/gui/file/{res['meta']['file_info']['sha256']}"
                        
                        await utils.answer(msg, self.strings("vt_report").format(
                            link=report_link, malicious=malicious, total=total,
                            status=self.strings("danger") if malicious > 0 else self.strings("clean"),
                            date=datetime.now().strftime("%d.%m.%Y %H:%M")
                        ) + heuristics)
                        self._last_scan = time.time()
                        return
            
            await utils.answer(msg, "⚠️ Анализ длится долго. Проверьте позже по ссылке на VT.")
        except Exception as e:
            logger.exception(e)
            await utils.answer(msg, f"❌ Ошибка: {str(e)}")
        finally:
            if os.path.exists(path): os.remove(path)

    @loader.command(ru_doc="Просмотреть код .py файла из ответа")
    async def getcodecmd(self, message: Message):
        reply = await message.get_reply_message()
        if not reply or not reply.file or not reply.file.name.endswith(".py"):
            await utils.answer(message, self.strings("no_file"))
            return

        if (reply.file.size / 1024) > self.config["max_code_kb"]:
            await utils.answer(message, self.strings("too_large").format(self.config["max_code_kb"]))
            return

        code = (await reply.download_media(bytes)).decode("utf-8", errors="replace")
        pages = [code[i:i+2000] for i in range(0, len(code), 2000)]
        session_id = f"{message.chat_id}_{message.id}"
        self._sessions[session_id] = {"pages": pages, "name": reply.file.name}

        await self._render_code(message, session_id, 0)

    async def _render_code(self, message_obj, session_id, page_index, call=None):
        session = self._sessions.get(session_id)
        if not session:
            if call: await call.answer(self.strings("session_expired"), show_alert=True)
            else: await utils.answer(message_obj, self.strings("session_expired"))
            return

        text = (
            self.strings("code_title").format(utils.escape_html(session["name"]), page_index + 1, len(session["pages"])) + 
            f"\n\n<pre>{utils.escape_html(session['pages'][page_index])}</pre>"
        )

        buttons = []
        if page_index > 0:
            buttons.append({"text": "⬅️", "callback": self._pager, "args": (session_id, page_index - 1)})
        if page_index < len(session["pages"]) - 1:
            buttons.append({"text": "➡️", "callback": self._pager, "args": (session_id, page_index + 1)})
        
        control_buttons = [{"text": "🚫 Закрыть", "action": "close"}]

        if call:
            await call.edit(text=text, reply_markup=[buttons, control_buttons] if buttons else [control_buttons])
        else:
            await self.inline.form(text=text, message=message_obj, reply_markup=[buttons, control_buttons] if buttons else [control_buttons])

    async def _pager(self, call, session_id, page_index):
        await self._render_code(None, session_id, page_index, call=call)
        await call.answer()