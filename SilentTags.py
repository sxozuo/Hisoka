"""
    🔕 SilentTags - Система защиты от тегов
    
    Бот отвечает на теги, логирует их и МОМЕНТАЛЬНО стирает 
    уведомление (собачку @) из списка чатов.
"""

# meta developer: @xyecoder
# meta banner: https://i.imgur.com/7OobOmW.jpeg
# scope: hikka_only
# scope: hikka_min 1.2.0

import logging
import asyncio
from .. import loader, utils
from herokutl.types import Message

logger = logging.getLogger(__name__)

@loader.tds
class SilentTagsMod(loader.Module):
    """Авто-ответ на теги, логирование и очистка уведомлений (@)"""
    
    # Твой новый баннер
    _banner = "https://i.imgur.com/7OobOmW.jpeg"
    
    strings = {
        "name": "SilentTags",
        "troll_text": "<b>🔇 Silent Tags включен. Ваше сообщение не было доставлено адресату.</b>",
        "log_template": (
            "<b>🔔 Новый пинг!</b>\n\n"
            "<b>👤 Отправитель:</b> {name} ({username})\n"
            "<b>💬 Сообщение:</b> <code>{text}</code>\n"
            "<b>📍 Чат:</b> {chat_title}\n"
            "<b>🔗 Ссылка:</b> <a href='{link}'>Перейти к сообщению</a>"
        ),
        "status_on": "<b>✅ SilentTags включен. Уведомления от @sxozuo будут скрываться.</b>",
        "status_off": "<b>❌ SilentTags выключен.</b>"
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._me = await client.get_me()
        if self._db.get("SilentTags", "state") is None:
            self._db.set("SilentTags", "state", True)

    @loader.command(ru_doc=" - Включить/выключить SilentTags")
    async def silenttagscmd(self, message: Message):
        """Переключает состояние модуля"""
        state = self._db.get("SilentTags", "state")
        new_state = not state
        self._db.set("SilentTags", "state", new_state)
        await utils.answer(message, self.strings("status_on") if new_state else self.strings("status_off"))

    @loader.watcher(only_messages=True, out=False)
    async def watcher(self, message: Message):
        """Следит за входящими пингами и чистит их"""
        if not self._db.get("SilentTags", "state"):
            return

        # Проверка на тег или реплай нам
        is_mention = message.mentioned
        is_reply_to_me = False
        
        if message.is_reply:
            reply_msg = await message.get_reply_message()
            if reply_msg and reply_msg.sender_id == self._me.id:
                is_reply_to_me = True

        if message.sender_id == self._me.id or not (is_mention or is_reply_to_me):
            return

        # Удаляем уведомление (@)
        try:
            await self._client.send_read_acknowledge(message.peer_id, message=message, clear_mentions=True)
        except Exception as e:
            logger.error(f"SilentTags fail to clear mention: {e}")

        # Отвечаем и запускаем таймер удаления
        async def send_and_delete():
            try:
                reply = await message.reply(self.strings("troll_text"))
                await asyncio.sleep(5)
                await reply.delete()
            except Exception:
                pass

        asyncio.create_task(send_and_delete())

        # Формируем лог в Избранное
        sender = await message.get_sender()
        name = utils.escape_html(getattr(sender, 'first_name', 'Неизвестно'))
        username = f"@{sender.username}" if getattr(sender, 'username', None) else "ID: " + str(sender.id)
        text = utils.escape_html(message.text or "Медиа/Стикер/ГС")
        chat = await message.get_chat()
        chat_title = utils.escape_html(getattr(chat, 'title', 'Личные сообщения'))
        
        # Ссылка
        if message.is_private:
            link = f"tg://user?id={sender.id}"
        else:
            chat_id = str(message.chat_id).replace("-100", "")
            link = f"https://t.me/c/{chat_id}/{message.id}"

        log_message = self.strings("log_template").format(
            name=name,
            username=username,
            text=text,
            chat_title=chat_title,
            link=link
        )

        try:
            await self._client.send_message("me", log_message)
        except Exception:
            pass
