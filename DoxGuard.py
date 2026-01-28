"""
    🛡️ DoxGuard — Anti-Dox & Privacy Patrol
    
    Продвинутый модуль для патрулирования чатов и автоматической защиты от слива персональных данных.
    Обнаруживает номера телефонов, банковские карты, паспорта и ФИО, наказывая нарушителей баном или мутом.
"""

version = (1, 0, 3)

# meta developer: @sxozuo
# meta pic: https://img.icons8.com/fluency/160/shield-with-check-mark.png
# scope: coddrago_only

import re
from datetime import timedelta
from .. import loader, utils

@loader.tds
class DoxGuardMod(loader.Module):
    """🛡️ Патрулирование чатов и защита от слива персональных данных (телефоны, карты, ФИО)."""
    
    strings = {
        "name": "DoxGuard"
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        if self.db.get("DoxGuard", "active_chats") is None:
            self.db.set("DoxGuard", "active_chats", [])

        self.phone_pattern = r"(?:\+?\d[\s\-\(\)]?){10,15}"
        self.other_ban = [
            r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",
            r"\b\d{2}[ ]?\d{2}[ ]?\d{6}\b",
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
        ]
        self.fio_pattern = r"\b[А-ЯЁ][а-яёё]+\s+[А-ЯЁ][а-яёё]+(?:\s+[А-ЯЁ][а-яёё]+)?\b"

    @loader.command()
    async def doxg(self, message):
        """Вкл/Выкл патруль в текущем чате/канале"""
        if message.is_private: 
            return await utils.answer(message, "<b>[DoxGuard]</b> Команда работает только в чатах/каналах.")
        
        chats = self.db.get("DoxGuard", "active_chats", [])
        if message.chat_id in chats:
            chats.remove(message.chat_id)
            res = "<b>[DoxGuard]</b> Патруль <b>ВЫКЛЮЧЕН</b>. ⚠️"
        else:
            chats.append(message.chat_id)
            res = "<b>[DoxGuard]</b> Патруль <b>ВКЛЮЧЕН</b>. 🛡"
        
        self.db.set("DoxGuard", "active_chats", chats)
        await utils.answer(message, res)

    @loader.command()
    async def gub(self, message):
        """Разбанить пользователя (убрать из ЧС)"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        target = args if args else (reply.sender_id if reply else None)
        
        if not target: 
            return await utils.answer(message, "Пользователя не существует, убедитесь в валидности аргументов⚠️")
        
        try:
            user_obj = await self.client.get_entity(int(target) if str(target).isdigit() else target)
            try:
                p = await self.client.get_permissions(message.chat_id, user_obj.id)
                if p.is_admin or p.is_creator or p.view_messages: 
                    return await utils.answer(message, "Пользователь уже разбанен🤯")
            except: 
                pass
            
            await self.client.edit_permissions(message.chat_id, user_obj.id, until_date=None, view_messages=True)
            return await utils.answer(message, "Пользователь разблокирован✅")
        except: 
            return await utils.answer(message, "Ошибка: У меня недостаточно прав! ❌")

    @loader.command()
    async def gum(self, message):
        """Размутить пользователя (вернуть право писать)"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        target = args if args else (reply.sender_id if reply else None)
        
        if not target: 
            return await utils.answer(message, "Пользователя не существует, убедитесь в валидности аргументов⚠️")
        
        try:
            user_obj = await self.client.get_entity(int(target) if str(target).isdigit() else target)
            try:
                p = await self.client.get_permissions(message.chat_id, user_obj.id)
                if p.is_admin or p.is_creator or p.send_messages: 
                    return await utils.answer(message, "Пользователь не в муте🤯")
            except: 
                pass
            
            await self.client.edit_permissions(message.chat_id, user_obj.id, until_date=None, send_messages=True)
            return await utils.answer(message, "Пользователь размучен✅")
        except: 
            return await utils.answer(message, "Ошибка: У меня недостаточно прав! ❌")

    async def watcher(self, message):
        chats = self.db.get("DoxGuard", "active_chats", [])
        if message.is_private or message.chat_id not in chats or not message.text: 
            return
        
        me = await self.client.get_me()
        if message.sender_id == me.id: 
            return

        text = message.text
        hit, mode = False, "mute"

        if re.search(self.phone_pattern, text):
            digits = "".join(filter(str.isdigit, text))
            if 10 <= len(digits) <= 15: 
                hit, mode = True, "ban"
        
        if not hit:
            for p in self.other_ban:
                if re.search(p, text): 
                    hit, mode = True, "ban"
                    break
        
        if not hit and re.search(self.fio_pattern, text): 
            hit, mode = True, "mute"

        if hit:
            try:
                p = await self.client.get_permissions(message.chat_id, message.sender_id)
                if p.is_admin or p.is_creator: 
                    return
                await self.punish(message, mode)
            except: 
                pass

    async def punish(self, message, mode):
        user = await message.get_sender()
        name = user.first_name if user.first_name else "Юзер"
        try:
            await message.delete()
            if mode == "ban":
                await self.client.edit_permissions(message.chat_id, user.id, view_messages=False)
                await message.respond(f"<b>[DoxGuard]</b> Пользователь <a href='tg://user?id={user.id}'>{name}</a> в <b>ЧЕРНОМ СПИСОКЕ</b> ❌.")
            else:
                if message.is_group:
                    await self.client.edit_permissions(message.chat_id, user.id, until_date=timedelta(days=1), send_messages=False)
                    await message.respond(f"<b>[DoxGuard]</b> Пользователь <a href='tg://user?id={user.id}'>{name}</a> в <b>МУТЕ</b> (24ч) за ФИО.")
                else:
                    await self.client.edit_permissions(message.chat_id, user.id, view_messages=False)
                    await message.respond(f"<b>[DoxGuard]</b> Пользователь <a href='tg://user?id={user.id}'>{name}</a> в <b>ЧЕРНОМ СПИСОКЕ</b> ❌.")
        except: 
            pass