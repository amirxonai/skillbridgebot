"""
handlers/admin.py — Admin commands (extended with inline panel and broadcast).
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import admin_keyboard, main_menu_keyboard
from skillbridge_bot.config import ADMIN_IDS

router = Router()


class BroadcastState(StatesGroup):
    waiting_message = State()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
@router.message(Command("admin_stats"))
async def cmd_admin(message: Message) -> None:
    user_id = message.from_user.id
    if not _is_admin(user_id):
        await message.answer("🚫 Sizda admin huquqlari yo'q.")
        return

    stats = storage.get_user_stats()
    await message.answer(
        f"🛡️ <b>SkillBridge Admin Panel</b>\n\n"
        f"📊 <b>Platformа Statistikasi:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🎓 Mentorlar: <b>{stats['total_mentors']}</b>\n"
        f"🤝 Faol juftliklar: <b>{stats['total_matches']}</b>\n"
        f"⏳ Navbatdagilar: <b>{stats['active_in_queue']}</b>\n"
        f"⭐ Baholashlar: <b>{stats['total_ratings']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if not _is_admin(user_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return
    await callback.answer()
    stats = storage.get_user_stats()
    await callback.message.answer(
        f"📊 <b>To'liq Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🎓 Mentorlar: <b>{stats['total_mentors']}</b>\n"
        f"🔄 Almashish ro'yxatkiylari: <b>{stats['total_users'] - stats['total_mentors']}</b>\n"
        f"🤝 Faol juftliklar: <b>{stats['total_matches']}</b>\n"
        f"⏳ Navbatdagilar: <b>{stats['active_in_queue']}</b>\n"
        f"⭐ Jami baholashlar: <b>{stats['total_ratings']}</b>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if not _is_admin(user_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return
    await callback.answer()
    users = storage.get_all_users()
    recent = users[-10:] if len(users) >= 10 else users
    recent.reverse()

    lines = [f"👥 <b>Oxirgi 10 foydalanuvchi</b>\n\n"]
    for u in recent:
        role_icon = "🎓" if u["user_type"] == "mentor" else "🔄"
        lines.append(
            f"{role_icon} @{u['username']} — "
            f"<code>{u['teach_skill'].title()}</code> → "
            f"<code>{u['learn_skill'].title()}</code>\n"
        )

    await callback.message.answer("".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "admin_mentors")
async def cb_admin_mentors(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if not _is_admin(user_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return
    await callback.answer()
    from skillbridge_bot.services import mentor_service
    mentors = mentor_service.get_top_mentors(limit=20)

    if not mentors:
        await callback.message.answer("😔 Hozirda tasdiqlangan mentorlar yo'q.")
        return

    lines = [f"🎓 <b>Barcha Mentorlar ({len(mentors)} ta)</b>\n\n"]
    for idx, m in enumerate(mentors, 1):
        rating_str = f"{m['rating']:.1f}⭐" if m["rating_count"] > 0 else "—"
        lines.append(
            f"{idx}. @{m['username']} — {m['teach_skill'].title()} | {rating_str}\n"
        )

    await callback.message.answer("".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "admin_queue")
async def cb_admin_queue(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if not _is_admin(user_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return
    await callback.answer()
    queue = storage.get_queue()

    if not queue:
        await callback.message.answer("✅ Navbat bo'sh — hamma match topdi!")
        return

    lines = [f"⏳ <b>Kutish navbati ({len(queue)} ta)</b>\n\n"]
    for uid in queue[:20]:
        u = storage.get_user(uid)
        if u:
            lines.append(
                f"• @{u['username']} — 📚 {u['teach_skill'].title()} → 🎯 {u['learn_skill'].title()}\n"
            )

    await callback.message.answer("".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    if not _is_admin(user_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        "📢 <b>Barcha foydalanuvchilarga xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabarni yozing:\n"
        "<i>('bekor' deb yozing — bekor qilish uchun)</i>",
        parse_mode="HTML",
    )
    await state.set_state(BroadcastState.waiting_message)


@router.message(BroadcastState.waiting_message)
async def process_broadcast(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if not _is_admin(user_id):
        await state.clear()
        return

    text = message.text.strip()
    if text.lower() in ("bekor", "cancel", "отмена"):
        await state.clear()
        await message.answer("❌ Xabar yuborish bekor qilindi.")
        return

    await state.clear()
    users = storage.get_all_users()
    success = 0
    fail = 0

    broadcast_text = f"📢 <b>SkillBridge E'loni</b>\n\n{text}"
    await message.answer(f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...")

    for u in users:
        try:
            await message.bot.send_message(
                chat_id=u["user_id"],
                text=broadcast_text,
                parse_mode="HTML",
            )
            success += 1
        except Exception:
            fail += 1

    await message.answer(
        f"✅ <b>Xabar yuborildi!</b>\n\n"
        f"✅ Muvaffaqiyatli: <b>{success}</b>\n"
        f"❌ Yuborilmadi: <b>{fail}</b>",
        parse_mode="HTML",
    )


# Mentor approve/reject callbacks
@router.callback_query(F.data.startswith("approve_mentor:"))
async def process_approve_mentor(callback: CallbackQuery) -> None:
    admin_id = callback.from_user.id
    if not _is_admin(admin_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return

    target_user_id = int(callback.data.split(":")[1])
    pending = storage.get_pending_mentor(target_user_id)

    if not pending:
        await callback.answer("❌ So'rov topilmadi yoki allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    storage.update_user(
        target_user_id,
        user_type="mentor",
        bio=pending["bio"],
        experience_level=pending["experience_level"],
    )
    storage.remove_pending_mentor(target_user_id)

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Admin tomonidan tasdiqlandi</b>",
        parse_mode="HTML",
        reply_markup=None,
    )
    await callback.answer("✅ Mentor tasdiqlandi!")

    try:
        user = storage.get_user(target_user_id)
        await callback.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"Sizning mentorlik so'rovingiz <b>tasdiqlandi</b>! ✅\n\n"
                f"Endi siz SkillBridge Mentorlar ro'yxatida ko'rinasiz.\n"
                f"Foydalanuvchilar siz bilan bog'lana boshlaydi! 🚀"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_mentor:"))
async def process_reject_mentor(callback: CallbackQuery) -> None:
    admin_id = callback.from_user.id
    if not _is_admin(admin_id):
        await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
        return

    target_user_id = int(callback.data.split(":")[1])
    storage.remove_pending_mentor(target_user_id)

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Admin tomonidan rad etildi</b>",
        parse_mode="HTML",
        reply_markup=None,
    )
    await callback.answer("❌ So'rov rad etildi.")

    try:
        await callback.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"😔 <b>So'rov holati</b>\n\n"
                f"Sizning mentorlik so'rovingiz hozircha rad etildi.\n\n"
                f"Biroq siz botdan bilim almashish uchun foydalanishda davom etishingiz mumkin!\n"
                f"Qayta ariza topshirish uchun /become_mentor ni bosing."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass
