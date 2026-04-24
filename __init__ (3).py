"""
handlers/profile.py — /profile command handler (modernized with inline buttons).
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import main_menu_keyboard, profile_inline_keyboard, cancel_keyboard
from skillbridge_bot.utils.helpers import format_timestamp
from skillbridge_bot.utils.i18n import _

router = Router()


class EditSkills(StatesGroup):
    teach = State()
    learn = State()


def _build_profile_card(user: dict, user_id: int) -> str:
    """Build a beautiful profile card with emojis."""
    rating_str = f"{user['rating']:.1f} ⭐" if user["rating_count"] > 0 else "—"
    joined_date = format_timestamp(user.get("created_at", ""))

    role_map = {
        "mentor": "🎓 Mentor",
        "exchange": "🔄 Bilim almashish",
        "learner": "📖 O'quvchi",
    }
    role_display = role_map.get(user.get("user_type", ""), user.get("user_type", "").title())

    stars = "⭐" * round(user["rating"]) if user["rating_count"] > 0 else ""

    bio_line = f"\n📝 <b>Bio:</b> {user['bio']}" if user.get("bio") else ""
    xp_line = f"\n🎖️ <b>Tajriba:</b> {user['experience_level']}" if user.get("experience_level") else ""

    return (
        f"┌─────────────────────────┐\n"
        f"│  👤 <b>SkillBridge Profil</b>   │\n"
        f"└─────────────────────────┘\n\n"
        f"👤 <b>Ism:</b>          @{user['username']}\n"
        f"🏷️ <b>Rol:</b>          {role_display}\n"
        f"📚 <b>O'rgatadi:</b>    <code>{user['teach_skill'].title()}</code>\n"
        f"🎯 <b>O'rganadi:</b>    <code>{user['learn_skill'].title()}</code>\n"
        f"⭐ <b>Reyting:</b>      {rating_str} {stars} ({user['rating_count']} sharh)\n"
        f"🤝 <b>Almashinuvlar:</b> {user['matches_count']}\n"
        f"📅 <b>Qo'shilgan:</b>   {joined_date}"
        f"{bio_line}{xp_line}\n\n"
        f"💡 <i>Quyidagi tugmalar orqali profilingizni boshqaring</i>"
    )


@router.message(Command("profile"))
@router.message(F.text.in_({"👤 Profile", "👤 My Profile", "👤 Profil", "👤 Профиль"}))
async def cmd_profile(message: Message) -> None:
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if not user:
        await message.answer(
            "⚠️ Siz hali ro'yxatdan o'tmagansiz!\n/start ni bosing.",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    await message.answer(
        _build_profile_card(user, user_id),
        parse_mode="HTML",
        reply_markup=profile_inline_keyboard(user_id),
    )


@router.callback_query(F.data == "edit_skills")
async def cb_edit_skills(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.answer(
        "✏️ <b>Ko'nikmalarni tahrirlash</b>\n\n"
        "📚 <b>1-qadam:</b> Nima o'rgata olasiz? (yangi ko'nikma nomini yozing)\n\n"
        "<i>Masalan: Python, Dizayn, Ingliz tili</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(EditSkills.teach)


@router.message(EditSkills.teach)
async def process_edit_teach(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    cancel_texts = {"❌ Cancel", "❌ Bekor qilish", "❌ Отмена"}

    if text in cancel_texts:
        await state.clear()
        await message.answer("❌ Tahrirlash bekor qilindi.", reply_markup=main_menu_keyboard(user_id))
        return

    if len(text) < 2:
        await message.answer("⚠️ Haqiqiy ko'nikma nomi kiriting.")
        return

    await state.update_data(teach=text)
    await message.answer(
        f"✅ O'rgatadi: <b>{text}</b>\n\n"
        f"🎯 <b>2-qadam:</b> Nima o'rganmoqchisiz?",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(EditSkills.learn)


@router.message(EditSkills.learn)
async def process_edit_learn(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    cancel_texts = {"❌ Cancel", "❌ Bekor qilish", "❌ Отмена"}

    if text in cancel_texts:
        await state.clear()
        await message.answer("❌ Tahrirlash bekor qilindi.", reply_markup=main_menu_keyboard(user_id))
        return

    if len(text) < 2:
        await message.answer("⚠️ Haqiqiy ko'nikma nomi kiriting.")
        return

    data = await state.get_data()
    teach = data["teach"]
    storage.update_user(user_id, teach_skill=teach.strip().lower(), learn_skill=text.strip().lower())
    await state.clear()

    await message.answer(
        f"✅ <b>Ko'nikmalar yangilandi!</b>\n\n"
        f"📚 O'rgatadi: <b>{teach.title()}</b>\n"
        f"🎯 O'rganadi: <b>{text.title()}</b>\n\n"
        f"⚡ Yangi match qidirish uchun menyudan foydalaning.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user_id),
    )


@router.callback_query(F.data == "open_rate")
async def cb_open_rate(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    from skillbridge_bot.keyboards.menu import rating_keyboard
    match_id = storage.get_match(user_id)
    if not match_id:
        await callback.message.answer(
            "🤷 Hozirda baholash uchun sherigingiz yo'q.\n\n"
            "Avval bilim almashishni bajaring!",
        )
        return
    partner = storage.get_user(match_id)
    storage.set_pending_rating(user_id, match_id)
    await callback.message.answer(
        f"⭐ <b>@{partner['username']}</b> bilan tajribangizni baholang:\n\n"
        f"Quyidagi yulduzchalardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=rating_keyboard(),
    )


@router.callback_query(F.data == "find_match")
async def cb_find_match(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer("🔍 Yangi match qidirmoqda...", show_alert=False)
    from skillbridge_bot.services import matcher
    match_result = matcher.find_match(user_id)
    if match_result:
        uid_a, uid_b = match_result
        partner_id = uid_b if uid_a == user_id else uid_a
        partner = storage.get_user(partner_id)
        storage.remove_from_queue(uid_a)
        storage.remove_from_queue(uid_b)
        storage.add_match(uid_a, uid_b)
        await callback.message.answer(
            f"🎉 <b>Yangi match topildi!</b>\n\n"
            f"👤 Sherik: <b>@{partner['username']}</b>\n"
            f"📚 O'rgatadi: <b>{partner['teach_skill'].title()}</b>\n"
            f"🎯 O'rganadi: <b>{partner['learn_skill'].title()}</b>\n\n"
            f"🚀 Ular bilan Telegram orqali bog'laning!",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id),
        )
    else:
        storage.add_to_queue(user_id)
        await callback.message.answer(
            "⏳ <b>Match topilmadi.</b>\n\n"
            "Siz kutish ro'yxatiga qo'shildingiz.\n"
            "Mos sherik topilganda xabar beramiz! 🔔",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id),
        )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.answer(
        "🏠 Asosiy menyu",
        reply_markup=main_menu_keyboard(user_id),
    )


@router.callback_query(F.data == "my_referrals")
async def cb_my_referrals(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.answer()
    count = storage.get_referral_count(user_id)
    await callback.message.answer(
        f"📊 <b>Sizning referallaringiz:</b>\n\n"
        f"👥 Siz taklif qilgan foydalanuvchilar: <b>{count} ta</b>\n\n"
        f"💡 Qancha ko'p odam taklif qilsangiz, platforma shunchalik rivojlanadi!",
        parse_mode="HTML",
    )
