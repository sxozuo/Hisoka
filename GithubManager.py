"""
    📦 GitHubManager - Управление репозиториями через GitHub API
    
    Этот модуль позволяет загружать (обновлять) файлы в указанный репозиторий GitHub
    с помощью REST API и персонального токена.
"""

__version__ = (6, 0, 1) # Версия с обновлением текста гайда

# meta developer: @sxozuo
# requires: aiohttp

import aiohttp
import base64
import logging
import json
from typing import Optional

from .. import loader, utils
from herokutl.types import Message

logger = logging.getLogger(__name__)

# URL для GitHub Content API: /repos/{owner}/{repo}/contents/{path}
GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"

@loader.tds
class GitHubManagerMod(loader.Module):
    """Управление файлами в репозиториях GitHub"""
    
    strings = {
        "name": "GitHubManager",
        "no_config": "❌ <b>Ошибка:</b> Пожалуйста, настройте <code>github_token</code> в конфиге модуля.",
        "no_repo_set": "❌ <b>Ошибка:</b> Репозиторий по умолчанию не установлен. Пожалуйста, укажите <code>repo_owner</code> и <code>repo_name</code> в конфиге модуля.",
        "no_reply": "❌ <b>Ошибка:</b> Ответьте на сообщение с файлом, который нужно загрузить.",
        "api_error": "❌ <b>GitHub API Ошибка (HTTP {status}):</b> {error}",
        "internal_error": "❌ <b>Внутренняя Ошибка:</b> {}",
        "no_filename": "❌ <b>Ошибка:</b> Не удалось определить имя файла из сообщения. Убедитесь, что это документ или медиафайл.",
        "downloading": "⏳ Скачиваю файл...",
        "uploading": "⏳ Загружаю файл в репозиторий <code>{owner}/{repo}</code> по пути <code>{path}</code>...",
        "success_create": "✅ <b>Файл создан:</b> <code>{path}</code>\nURL: {url}",
        "success_update": "✅ <b>Файл обновлен:</b> <code>{path}</code>\nURL: {url}",
        "info_guide": (
            "🚀 <b>Гайд по модулю GitHubManager</b>\n\n"
            "Этот модуль позволяет загружать файлы в ваш репозиторий GitHub.\n\n"
            "### ⚙️ Настройка (Обязательно)\n"
            "1. Получите Персональный Токен (PAT) на GitHub с правами <code>repo</code>.\n"
            "2. **Установите в конфиге модуля следующие параметры:**\n"
            "   - <code>github_token</code>: Ваш PAT.\n"
            "   - <code>repo_owner</code>: Владелец целевого репозитория (например, <code>sxozuo</code>).\n"
            "   - <code>repo_name</code>: Имя целевого репозитория (например, <code>userbot_files</code>).\n\n"
            "### 💾 Использование\n"
            "Команда: <code>.ghupload</code> [сообщение коммита]\n"
            "<b>Действие:</b> Ответьте этой командой на сообщение с файлом.\n"
            "   - Файл будет загружен или обновлен (если уже существует).\n"
            "   - <b>[сообщение коммита]</b> — опционально. Если не указано, используется имя файла."
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "github_token",
                "",
                "Персональный токен GitHub (PAT) с правами 'repo'",
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                "repo_owner",
                "",
                "Владелец репозитория (устанавливается только через конфиг)",
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "repo_name",
                "",
                "Название репозитория (устанавливается только через конфиг)",
                validator=loader.validators.String()
            ),
        )

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self.session = None

    async def on_unload(self):
        if hasattr(self, "session") and self.session and not self.session.closed:
            await self.session.close()

    async def _ensure_session(self):
        """Создает или пересоздает асинхронную сессию aiohttp с актуальным токеном."""
        if self.session and not self.session.closed:
            return
        
        token = self.config['github_token'].strip()
        if not token:
            return
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Heroku-UserBot-GitHubManager",
        }
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    @loader.command(
        ru_doc="Показывает мини-гайд по настройке и использованию модуля.",
        en_doc="Shows a mini-guide on how to set up and use the module."
    )
    async def ghinfocmd(self, message: Message):
        """Показывает мини-гайд по модулю GitHubManager."""
        await utils.answer(message, self.strings("info_guide"))
        
    @loader.command(
        ru_doc="[сообщение коммита] - Загружает файл из ответа. Использует оригинальное имя файла. Сообщение коммита опционально.",
        en_doc="[commit message] - Uploads file from reply. Uses original file name. Commit message is optional."
    )
    async def ghuploadcmd(self, message: Message):
        """Upload/update a file to GitHub repository."""
        if not self.config["github_token"]:
            await utils.answer(message, self.strings("no_config"))
            return
        
        owner = self.config["repo_owner"]
        repo = self.config["repo_name"]
        
        if not owner or not repo:
            await utils.answer(message, self.strings("no_repo_set"))
            return

        reply = await message.get_reply_message()
        if not reply or not (reply.media):
            await utils.answer(message, self.strings("no_reply"))
            return
            
        file_path = None
        
        media_entity = reply.document or reply.photo or reply.video or reply.audio
        
        if media_entity:
            file_path = getattr(media_entity, 'file_name', None)
            
            if not file_path:
                file_path = getattr(media_entity, 'name', None)
                
            if not file_path and getattr(media_entity, 'attributes', None):
                for attr in media_entity.attributes:
                    if hasattr(attr, 'file_name'):
                        file_path = attr.file_name
                        break
            
            if not file_path and reply.photo:
                file_path = f"{media_entity.file_id}.jpg"


        if not file_path:
            await utils.answer(message, self.strings("no_filename"))
            return
        
        commit_message = utils.get_args_raw(message).strip()
        
        if not commit_message:
            commit_message = f"File upload: {file_path}"


        status_message = await utils.answer(message, self.strings("downloading"))
        
        try:
            file_bytes = await reply.download_media(bytes)
        except Exception as e:
            await utils.answer(status_message, self.strings("internal_error").format(f"Скачивание файла: {e}"))
            logger.exception(e)
            return

        await self._ensure_session()
        await self._upload_file(status_message, file_bytes, owner, repo, file_path, commit_message)

    async def _upload_file(self, message: Message, content_bytes: bytes, owner: str, repo: str, path: str, commit_msg: str):
        """Основная логика загрузки/обновления файла через GitHub API."""
        url = GITHUB_API_URL.format(owner=owner, repo=repo, path=path.lstrip('/'))
        
        await utils.answer(message, self.strings("uploading").format(owner=utils.escape_html(owner), repo=utils.escape_html(repo), path=utils.escape_html(path)))
        
        try:
            async with self.session.get(url) as response:
                sha = None
                if response.status == 200:
                    file_data = await response.json()
                    sha = file_data.get("sha")
                elif response.status == 404:
                    pass
                else:
                    error_json = await response.json()
                    error_message = error_json.get("message", "Неизвестная ошибка")
                    raise aiohttp.ClientResponseError(
                        response.request_info, response.history, 
                        status=response.status, 
                        message=error_message
                    )

            encoded_content = base64.b64encode(content_bytes).decode('utf-8')

            payload = {
                "message": commit_msg,
                "content": encoded_content,
            }
            if sha:
                payload["sha"] = sha
            
            async with self.session.put(url, json=payload) as response:
                response_json = await response.json()
                
                if response.status in (200, 201):
                    commit_type = "create" if response.status == 201 else "update"
                    download_url = response_json["content"]["download_url"]
                    
                    if commit_type == "create":
                        result_string = self.strings("success_create").format(
                            path=utils.escape_html(path),
                            url=download_url
                        )
                    else:
                        result_string = self.strings("success_update").format(
                            path=utils.escape_html(path),
                            url=download_url
                        )
                    
                    await utils.answer(message, result_string)
                else:
                    error_message = response_json.get("message", "Неизвестная ошибка")
                    error_string = self.strings("api_error").format(
                        status=response.status,
                        error=utils.escape_html(error_message)
                    )
                    await utils.answer(message, error_string)

        except aiohttp.ClientResponseError as e:
            error_string = self.strings("api_error").format(
                status=e.status,
                error=utils.escape_html(e.message)
            )
            await utils.answer(message, error_string)
            logger.exception(e)

        except Exception as e:
            await utils.answer(message, self.strings("internal_error").format(str(e)))
            logger.exception(e)