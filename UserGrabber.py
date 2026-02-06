"""
    🛰 UserGrabber - Перехват освободившихся юзернеймов
    
    Мониторит юзернейм цели. Как только он освобождается, 
    бот создает канал и занимает этот юзернейм.
"""

# meta developer: @xyecoder
# meta banner: https://pomf2.lain.la/f/70gfplrv.jpg
# scope: hikka_only
# scope: hikka_min 1.2.0

import logging
import asyncio
from herokutl.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest
from herokutl.tl.functions.contacts import ResolveUsernameRequest
from herokutl.errors import UsernameNotOccupiedError, FloodWaitError
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class UserGrabberMod(loader.Module):
    """Мониторинг и перехват юзернеймов"""
    
    _banner = "https://i.imgur.com/7OobOmW.jpeg"
    
    strings = {
        "name": "UserGrabber",
        "started": "<b>🛰 Мониторинг запущен!</b>\nЦель: <code>@{}</code>\n<i>Бот займет ник, как только он освободится.</i>",
        "invalid_args": "<b>❌ Укажи юзернейм без @.</b>\nПример: <code>.username target_nick</code>",
        "already_running": "<b>⚠️ Мониторинг уже идет за другой целью.</b>",
        "stopped": "<b>🛑 Мониторинг остановлен.</b>",
        "success": "<b>✅ Юзернейм @{} ПЕРЕХВАЧЕН!</b>\nКанал создан.",
        "limit_error": "<b>❌ Ошибка: лимит публичных каналов исчерпан или FloodWait.</b>",
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        # Инициализируем переменные при запуске
        self._target = None
        self._task = None

    @loader.command(
        ru_doc="<username> - Начать слежку за юзернеймом (без @)",
        en_doc="<username> - Start monitoring a username"
    )
    async def usernamecmd(self, message):
        """Запустить перехватчик"""
        # Безопасная проверка существования атрибутов
        if not hasattr(self, '_task'):
            self._task = None
        if not hasattr(self, '_target'):
            self._target = None

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("invalid_args"))
            return
        
        target = args.strip().replace("@", "")
        
        if self._task and not self._task.done():
            await utils.answer(message, self.strings("already_running"))
            return

        self._target = target
        self._task = asyncio.create_task(self._grabber_loop())
        
        await utils.answer(message, self.strings("started").format(target))

    @loader.command(ru_doc=" - Остановить слежку")
    async def stopgrabcmd(self, message):
        """Остановить перехватчик"""
        task = getattr(self, '_task', None)
        if task and not task.done():
            task.cancel()
            self._task = None
            self._target = None
            await utils.answer(message, self.strings("stopped"))
        else:
            await utils.answer(message, "<b>❌ Мониторинг не запущен.</b>")

    async def _grabber_loop(self):
        """Цикл проверки юзернейма"""
        logger.info(f"Starting grabber loop for @{self._target}")
        
        while self._target:
            try:
                # Пробуем разрешить юзернейм
                await self._client(ResolveUsernameRequest(self._target))
                # Если ошибки нет — значит юзернейм всё еще занят
                logger.info(f"@{self._target} is still occupied.")
                
            except UsernameNotOccupiedError:
                # ЮЗЕРНЕЙМ СВОБОДЕН!
                logger.info(f"@{self._target} IS FREE! Attempting to snatch...")
                success = await self._snatch_username()
                if success:
                    await self._client.send_message("me", self.strings("success").format(self._target))
                    self._target = None
                    self._task = None
                    break
                    
            except FloodWaitError as e:
                logger.warning(f"FloodWait for {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Grabber loop error: {e}")

            # Пауза 20 секунд (безопасно для лимитов)
            await asyncio.sleep(20)

    async def _snatch_username(self):
        """Создание канала и установка юзернейма"""
        try:
            # 1. Создаем канал
            created_chat = await self._client(CreateChannelRequest(
                title=f"Reserved @{self._target}",
                about="This username has been snatched by UserGrabber.",
                megagroup=False
            ))
            
            # В Telethon результат CreateChannelRequest возвращает объект Updates
            # Находим там ID созданного канала
            channel = created_chat.chats[0]
            
            # 2. Пытаемся поставить юзернейм
            await self._client(UpdateUsernameRequest(
                channel=channel,
                username=self._target
            ))
            return True
            
        except Exception as e:
            logger.error(f"Snatch failed: {e}")
            return False