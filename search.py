"""
handlers/invite.py — Referral/invite system (modernized with inline share button).
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from skillbridge_bot.config import BOT_USERNAME
from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import main_menu_keyboard, invite_keyboard
from skillbridge_bot.utils.i18n import _

router = Router()


@router.message(Command("invite"))
@router.message(F.text.in_({"📨 Invite", "📨 Invite Friends", "🎁 Do'stlarni taklif qilish", "🎁 Пригласить друзей"}))
async def cmd_invite(message: Message) -> None:
    user_id = message.from_user.id
    invite_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    ref_count = storage.get_referral_count(user_id)

    await message.answer(
        f"🎁 <b>Do'stlarni SkillBridge-ga taklif qiling!</b>\n\n"
        f"📊 <b>Sizning referallaringiz:</b> {ref_count} ta\n\n"
        f"🔗 <b>Sizning havola:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>Nima uchun taklif qilish kerak?</b>\n"
        f"• Platforma rivojlanadi va ko'p match topiladi\n"
        f"• Do'stingiz siz bilan bilim almashishi mumkin\n"
        f"• O'zbek ta'limini birga rivojlantiramiz 🇺🇿\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Quyidagi tugma orqali ulashing:",
        parse_mode="HTML",
        reply_markup=invite_keyboard(invite_link),
    )


@router.callback_query(F.data == "my_referrals")
async def cb_my_referrals(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    count = storage.get_referral_count(user_id)

    # Build progress bar
    max_level = 10
    filled = min(count, max_level)
    bar = "🟩" * filled + "⬜" * (max_level - filled)

    level_text = ""
    if count >= 10:
        level_text = "🏆 <b>Champion</b> — Siz top referral!"
    elif count >= 5:
        level_text = "🥈 <b>Pro</b> — 5+ ta do'st taklif qildingiz!"
    elif count >= 1:
        level_text = "🥉 <b>Starter</b> — Siz birinchi qadamni bosdiingiz!"
    else:
        level_text = "⭐ Hali hech kim taklif qilinmagan"

    await callback.message.answer(
        f"📊 <b>Mening Referallarim</b>\n\n"
        f"{bar}\n"
        f"👥 Taklif qilinganlar: <b>{count} ta</b>\n\n"
        f"{level_text}\n\n"
        f"💡 <i>Do'stlaringizni taklif qiling va SkillBridge-ni O'zbekistonda mashhur qiling!</i>",
        parse_mode="HTML",
    )
