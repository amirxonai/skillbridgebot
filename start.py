"""
handlers/mentors.py — Mentor platform commands (modernized with inline keyboards).
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

from skillbridge_bot.data import storage
from skillbridge_bot.services import mentor_service
from skillbridge_bot.keyboards.menu import (
    main_menu_keyboard, cancel_keyboard,
    mentor_detail_keyboard, mentors_nav_keyboard
)
from skillbridge_bot.utils.i18n import _
from skillbridge_bot.config import ADMIN_IDS

router = Router()

PAGE_SIZE = 5


class MentorReg(StatesGroup):
    bio = State()
    experience = State()


def _mentor_card(idx: int, m: dict) -> str:
    rating_str = f"{m['rating']:.1f} ⭐" if m["rating_count"] > 0 else "🆕 Yangi"
    exp_str = f" | 🎖️ {m['experience_level']}" if m.get("experience_level") else ""
    bio_str = f"\n   📝 {m['bio'][:80]}..." if m.get("bio") and len(m["bio"]) > 80 \
        else (f"\n   📝 {m['bio']}" if m.get("bio") else "")
    return (
        f"<b>{idx}.</b> @{m['username']} ✅\n"
        f"   📚 <b>{m['teach_skill'].title()}</b>{exp_str}\n"
        f"   ⭐ {rating_str}  |  🤝 {m['matches_count']} ta seans"
        f"{bio_str}\n\n"
    )


@router.message(Command("mentors"))
@router.message(F.text.in_({"🎓 Top Mentors", "🎓 Mentors", "🎓 Mentorlar", "🎓 Менторы"}))
async def cmd_list_mentors(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    all_mentors = mentor_service.get_top_mentors(limit=50)

    if not all_mentors:
        await message.answer(
            "😔 <b>Hozirda mentorlar yo'q.</b>\n\n"
            "Siz birinchi bo'lib /become_mentor orqali mentor bo'lishingiz mumkin! 🎓",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    total_pages = (len(all_mentors) + PAGE_SIZE - 1) // PAGE_SIZE
    page = 0
    page_mentors = all_mentors[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = [
        f"🎓 <b>SkillBridge Top Mentorlari</b>\n"
        f"<i>Jami {len(all_mentors)} ta tasdiqlangan mentor</i>\n\n"
    ]
    for idx, m in enumerate(page_mentors, start=1):
        lines.append(_mentor_card(idx, m))

    await message.answer(
        "".join(lines),
        parse_mode="HTML",
        reply_markup=mentors_nav_keyboard(page, total_pages) if total_pages > 1 else main_menu_keyboard(user_id),
    )
    if total_pages > 1:
        await state.update_data(mentor_ids=[m["user_id"] for m in all_mentors])


@router.callback_query(F.data.startswith("mentors_page:"))
async def cb_mentors_page(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    mentor_ids = data.get("mentor_ids", [])
    all_mentors = [storage.get_user(uid) for uid in mentor_ids if storage.get_user(uid)]

    total_pages = (len(all_mentors) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_mentors = all_mentors[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = [
        f"🎓 <b>SkillBridge Top Mentorlari</b>\n"
        f"<i>Sahifa {page+1}/{total_pages}</i>\n\n"
    ]
    for idx, m in enumerate(page_mentors, start=1 + page * PAGE_SIZE):
        lines.append(_mentor_card(idx, m))

    await callback.message.edit_text(
        "".join(lines),
        parse_mode="HTML",
        reply_markup=mentors_nav_keyboard(page, total_pages),
    )


@router.callback_query(F.data == "become_mentor")
@router.message(Command("become_mentor"))
async def cmd_become_mentor(update, state: FSMContext) -> None:
    if isinstance(update, CallbackQuery):
        message = update.message
        user_id = update.from_user.id
        await update.answer()
    else:
        message = update
        user_id = update.from_user.id

    if not storage.user_exists(user_id):
        await message.answer(
            "⚠️ Avval ro'yxatdan o'ting!\n/start ni bosing.",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    user = storage.get_user(user_id)
    if user["user_type"] == "mentor":
        await message.answer(
            "🎓 <b>Siz allaqachon Mentorsiz!</b>\n\n"
            "Profilingiz mentorlar ro'yxatida ko'rinmoqda. 🌟",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    await message.answer(
        "🎓 <b>SkillBridge Mentori Bo'lish</b>\n\n"
        "Mentorlar boshqalarga bilim ulashadi va platformada alohida ko'rinadi.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 <b>1/2-qadam:</b> O'zingiz va tajribangiz haqida qisqacha yozing.\n\n"
        "<i>Masalan: '5 yillik Python dasturchiman, ko'plab loyihalar yaratganman...'</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(MentorReg.bio)


@router.message(MentorReg.bio)
async def process_mentor_bio(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    cancel_texts = {"❌ Cancel", "❌ Bekor qilish", "❌ Отмена", "/cancel"}

    if text in cancel_texts:
        await state.clear()
        await message.answer(
            "❌ Mentorlik so'rovi bekor qilindi.",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    if len(text) < 20:
        await message.answer(
            "⚠️ Bio juda qisqa! Kamida 20 ta harf yozing.\n\n"
            "<i>O'zingiz haqida ko'proq ma'lumot bering.</i>",
            parse_mode="HTML",
        )
        return

    await state.update_data(bio=text)
    await message.answer(
        f"✅ <b>Bio saqlandi!</b>\n\n"
        f"🎖️ <b>2/2-qadam:</b> Tajriba darajangizni yozing.\n\n"
        f"<i>Masalan: '5 yillik sanoat tajribasi', 'Senior Developer', '3 yil o'qtitish'</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(MentorReg.experience)


@router.message(MentorReg.experience)
async def process_mentor_exp(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    cancel_texts = {"❌ Cancel", "❌ Bekor qilish", "❌ Отмена", "/cancel"}

    if text in cancel_texts:
        await state.clear()
        await message.answer(
            "❌ Mentorlik so'rovi bekor qilindi.",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    data = await state.get_data()
    bio = data["bio"]
    experience = text

    storage.add_pending_mentor(user_id, bio=bio, experience_level=experience)
    await state.clear()

    await message.answer(
        "⏳ <b>So'rovingiz yuborildi!</b>\n\n"
        "Mentorlik so'rovingiz admin tomonidan ko'rib chiqilmoqda.\n"
        "Tekshirilgandan so'ng sizga xabar beramiz. 🔔\n\n"
        "<i>Odatda 24 soat ichida javob beriladi.</i>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user_id),
    )

    # Notify admins
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_mentor:{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_mentor:{user_id}"),
        ]
    ])

    admin_msg = (
        f"🆕 <b>Yangi Mentorlik So'rovi</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> @{message.from_user.username or 'nomalum'}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"📚 <b>O'rgatadi:</b> {storage.get_user(user_id)['teach_skill'].title()}\n"
        f"📝 <b>Bio:</b> {bio}\n"
        f"🎖️ <b>Tajriba:</b> {experience}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                parse_mode="HTML",
                reply_markup=admin_kb,
            )
        except Exception:
            continue
