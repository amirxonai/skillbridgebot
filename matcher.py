"""
handlers/skills.py — Skill Communities command.
/skills — Show all available categories taught on the platform.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from skillbridge_bot.services import mentor_service
from skillbridge_bot.keyboards.menu import main_menu_keyboard
from skillbridge_bot.utils.i18n import _

router = Router()

@router.message(Command("skills"))
@router.message(F.text.in_({"🌐 Skill Communities", "📚 Skills", "📚 Ko'nikmalar", "📚 Навыки"}))
async def cmd_skills(message: Message) -> None:
    user_id = message.from_user.id
    categories = mentor_service.get_skill_categories()

    if not categories:
        await message.answer(_("no_skills", user_id))
        return

    lines = [_("skills_header", user_id)]
    for skill, count in categories.items():
        if count == 1:
            lines.append(_("skills_item_single", user_id, skill=skill.title(), count=count))
        else:
            lines.append(_("skills_item_multi", user_id, skill=skill.title(), count=count))
            
    lines.append(_("skills_footer", user_id))

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu_keyboard(user_id))
