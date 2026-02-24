"""
    🧹 CommentCleaner - Убирает комментарии ИИ из кода

    Чистит код от мусорных комментариев нейросетей.
    Поддерживает Python, JS/TS, C/C++, Java, Go, Rust, PHP, CSS и другие.

    Использование:
    - Ответь на сообщение / файл (.py или .txt) командой .cc
    - Или вставь код прямо в команду: .cc <код>

    Результат всегда отправляется как clear_code.py
"""

version = (1, 1, 5)

# meta developer: @xyecoder
# meta banner: https://x0.at/ZcU1.jpg
# scope: hikka_only

from .. import loader, utils
from herokutl.types import Message
import logging
import re
import io
import os

logger = logging.getLogger(__name__)


@loader.tds
class CommentCleanerMod(loader.Module):
    """Убирает комментарии ИИ из кода"""

    version = (1, 1, 5)

    strings = {
        "name": "CommentCleaner",
        "no_code": (
            "❌ <b>No code provided.</b>\n"
            "Reply to a message / .py / .txt file or paste code after the command."
        ),
        "nothing": "🤷 <b>No comments found.</b> Code is already clean.",
        "error": "❌ <b>Processing error:</b> <code>{}</code>",
        "sending": "⏳ Cleaning and sending file...",
        "done": "✅ Comments removed: <code>{}</code>",
    }

    strings_ru = {
        "no_code": (
            "❌ <b>Нет кода.</b>\n"
            "Ответь на сообщение / .py / .txt файл или вставь код после команды."
        ),
        "nothing": "🤷 <b>Комментариев не найдено.</b> Код уже чистый.",
        "error": "❌ <b>Ошибка при обработке:</b> <code>{}</code>",
        "sending": "⏳ Чищу и отправляю файл...",
        "done": "✅ Убрано комментариев: <code>{}</code>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "strip_empty_lines",
                True,
                "",
                validator=loader.validators.Boolean(),
            ),
        )

    def _detect_lang(self, code: str) -> str:
        first = code[:300]
        checks = [
            (r"\bdef\b|\bimport\b|\belif\b|\bprint\s*\(", "python"),
            (r"\bconst\b|\blet\b|\bvar\b|\b=>\b|\bconsole\.log\b", "javascript"),
            (r":\s*\w+[\s\n]*[{;]|fun\s+\w+\s*\(|val\s+", "kotlin"),
            (r"#include|std::|cout|cin|->|::", "cpp"),
            (r"\bpackage\s+\w+|\bfunc\s+\w+\s*\(|\bfmt\.Print", "go"),
            (r"\bfn\s+\w+|\blet\s+mut\b|\bimpl\b|\buse\s+std", "rust"),
            (r"<\?php|\$\w+\s*=|echo\s+", "php"),
            (r"\bpublic\s+class\b|\bSystem\.out\b", "java"),
            (r"^\s*[\.\#]\w+\s*\{|margin:|padding:|color:", "css"),
        ]
        for pattern, lang in checks:
            if re.search(pattern, first, re.MULTILINE | re.IGNORECASE):
                return lang
        return "python"

    def _clean(self, code: str, lang: str) -> tuple[str, int]:
        removed = 0
        placeholders: dict[str, str] = {}
        ph_idx = 0

        def protect_string(m: re.Match) -> str:
            nonlocal ph_idx
            key = f"\x00STR{ph_idx}\x00"
            ph_idx += 1
            placeholders[key] = m.group(0)
            return key

        code = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', protect_string, code)
        code = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', protect_string, code)
        code = re.sub(r'`(?:\\.|[^`\\])*`', protect_string, code)

        if lang != "python":
            before = code
            code = re.sub(r'/\*[\s\S]*?\*/', '', code)
            removed += before.count('/*') - code.count('/*')

        if lang not in ("python", "css"):
            parts = code.split('\n')
            new_parts = []
            for line in parts:
                cl = re.sub(r'//.*$', '', line)
                if cl != line:
                    removed += 1
                new_parts.append(cl)
            code = '\n'.join(new_parts)

        if lang == "python":
            parts = code.split('\n')
            new_parts = []
            for line in parts:
                stripped = line.lstrip()
                if stripped.startswith('#!') or re.match(r'#.*coding[=:]\s*\S+', stripped):
                    new_parts.append(line)
                    continue
                cl = re.sub(r'#.*$', '', line)
                if cl != line:
                    removed += 1
                new_parts.append(cl)
            code = '\n'.join(new_parts)

        if lang == "css":
            parts = code.split('\n')
            new_parts = []
            for line in parts:
                cl = re.sub(r'//.*$', '', line)
                if cl != line:
                    removed += 1
                new_parts.append(cl)
            code = '\n'.join(new_parts)

        for key, val in placeholders.items():
            code = code.replace(key, val)

        if self.config["strip_empty_lines"]:
            code = re.sub(r'\n{3,}', '\n\n', code)
            code = code.strip()

        if lang == "python":
            code = self._fix_empty_blocks(code)

        return code, removed

    def _fix_empty_blocks(self, code: str) -> str:
        lines = code.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            result.append(line)
            stripped = line.rstrip()
            if stripped.endswith(':') and not stripped.lstrip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                block_indent = indent + 4
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j >= len(lines) or (len(lines[j]) - len(lines[j].lstrip())) <= indent:
                    result.append(' ' * block_indent + 'pass')
            i += 1
        return '\n'.join(result)

    def _extract(self, text: str) -> tuple[str, str]:
        blocks = re.findall(r'```(\w*)\n([\s\S]+?)```', text)
        if blocks:
            lang, code = max(blocks, key=lambda b: len(b[1]))
            return code, lang or ""
        return text.strip(), ""

    @loader.command(
        ru_doc="[код] — убрать комментарии ИИ, получить чистый .py файл",
        en_doc="[code] — strip AI comments, get clean .py file",
    )
    async def cc(self, message: Message):
        raw_args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        raw_code = None
        hint_lang = ""

        if reply and reply.document:
            doc = reply.document
            fname = ""
            for attr in doc.attributes:
                if hasattr(attr, "file_name"):
                    fname = attr.file_name
                    break
            ext = os.path.splitext(fname)[-1].lower()

            if ext in (".py", ".txt"):
                await utils.answer(message, self.strings("sending"))
                try:
                    file_bytes = await reply.download_media(bytes)
                    raw_code = file_bytes.decode("utf-8", errors="replace")
                    hint_lang = "python"
                except Exception as e:
                    logger.exception(e)
                    await utils.answer(message, self.strings("error").format(utils.escape_html(str(e))))
                    return

        if raw_code is None and raw_args:
            raw_code = raw_args

        if raw_code is None and reply and reply.text:
            raw_code = reply.text

        if raw_code is None:
            await utils.answer(message, self.strings("no_code"))
            return

        try:
            code, hl = self._extract(raw_code)
            lang = hint_lang or hl or self._detect_lang(code)
            cleaned, count = self._clean(code, lang)
        except Exception as e:
            logger.exception(e)
            await utils.answer(message, self.strings("error").format(utils.escape_html(str(e))))
            return

        if count == 0:
            await utils.answer(message, self.strings("nothing"))
            return

        file_obj = io.BytesIO(cleaned.encode("utf-8"))
        file_obj.name = "clear_code.py"

        await utils.answer_file(
            message,
            file_obj,
            caption=self.strings("done").format(count),
        )
