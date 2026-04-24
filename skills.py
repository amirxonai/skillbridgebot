"""
handlers/lang.py — Language switching handler.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import language_keyboard, main_menu_keyboard
from skillbridge_bot.utils.i18n import _

router = Router()

@router.message(Command("lang"))
@router.message(F.text.in_({"🌐 Til", "🌐 Язык", "🌐 Language"}))
async def cmd_lang(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer(
        _("choose_language", user_id),
        reply_markup=language_keyboard(),
    )

@router.message(F.text.contains("O'zbekcha"))
@router.message(F.text.contains("Русский"))
@router.message(F.text.contains("English"))
async def process_lang_switch(message: Message) -> None:
    user_id = message.from_user.id
    text = message.text
    
    if "O'zbekcha" in text:
        lang_code = "uz"
    elif "Русский" in text:
        lang_code = "ru"
    else:
        lang_code = "en"

    storage.set_user_language(user_id, lang_code)
    
    await message.answer(
        _("language_set", user_id),
        reply_markup=main_menu_keyboard(user_id),
    )
