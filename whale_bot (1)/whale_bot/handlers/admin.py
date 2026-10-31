from aiogram import F, Router
from aiogram.types import Message

from config import settings

router = Router()


@router.message(F.from_user.id == settings.admin_id, F.photo | F.audio | F.voice | F.document)
async def show_file_id(message: Message):
    """Админ присылает боту файл — бот отвечает его file_id для вставки в questions.json."""
    if message.photo:
        kind, fid = "photo", message.photo[-1].file_id  # последний размер — самый большой
    elif message.audio:
        kind, fid = "audio", message.audio.file_id
    elif message.voice:
        kind, fid = "voice", message.voice.file_id
    else:
        kind, fid = "document", message.document.file_id
    await message.reply(f"<b>{kind}</b> file_id:\n<code>{fid}</code>")
