"""
handlers/search.py — /find command handler with FSM-based search and pagination.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from skillbridge_bot.keyboards.menu import main_menu_keyboard, search_results_keyboard
from skillbridge_bot.services import matcher
from skillbridge_bot.utils.i18n import _
from skillbridge_bot.data import storage

router = Router()

PAGE_SIZE = 5


class SearchState(StatesGroup):
    waiting_skill = State()


def _format_user_card(idx: int, user: dict, user_id: int) -> str:
    rating_str = f"{user['rating']:.1f} ⭐" if user["rating_count"] > 0 else "—"
    verified = " ✅" if user.get("user_type") == "mentor" else ""
    return (
        f"<b>{idx}.</b> @{user['username']}{verified}\n"
        f"   📚 O'rgatadi: <b>{user['teach_skill'].title()}</b>\n"
        f"   🎯 O'rganadi: <b>{user['learn_skill'].title()}</b>\n"
        f"   ⭐ Reyting: {rating_str}  |  🤝 {user['matches_count']} ta almashish\n"
    )


@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "🔍 <b>O'qituvchi izlash</b>\n\n"
            "Qidirmoqchi bo'lgan ko'nikmani yozing:\n\n"
            "<i>Masalan: python, dizayn, ingliz tili</i>",
            parse_mode="HTML",
        )
        await state.set_state(SearchState.waiting_skill)
        return

    await _do_search(message, parts[1].strip(), state, user_id)


@router.message(F.text.in_({"🔍 Find Teachers", "🔍 Find Skills", "🔍 O'qituvchi izlash", "🔍 Найти учителя"}))
async def btn_find_skills(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await message.answer(
        "🔍 <b>O'qituvchi izlash</b>\n\n"
        "Qidirmoqchi bo'lgan ko'nikmani yozing:\n\n"
        "<i>Masalan: python, dizayn, ingliz tili, musiqa</i>",
        parse_mode="HTML",
    )
    await state.set_state(SearchState.waiting_skill)


@router.message(SearchState.waiting_skill)
async def process_search_input(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    skill = message.text.strip()

    cancel_texts = {"❌ Cancel", "❌ Bekor qilish", "❌ Отмена"}
    if skill in cancel_texts or skill.startswith("/"):
        await state.clear()
        await message.answer("❌ Qidiruv bekor qilindi.", reply_markup=main_menu_keyboard(user_id))
        return

    await state.clear()
    await _do_search(message, skill, state, user_id)


async def _do_search(message: Message, skill: str, state: FSMContext, user_id: int) -> None:
    results = matcher.search_teachers(skill)

    if not results:
        await message.answer(
            f"😔 <b>{skill.title()}</b> bo'yicha o'qituvchilar topilmadi.\n\n"
            f"💡 Siz o'sha ko'nikmani o'rgatsangiz, /start orqali ro'yxatdan o'ting!",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    page = 0
    page_results = results[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = [f"🔍 <b>\"{skill.title()}\" o'qituvchilari</b> — {len(results)} ta topildi\n\n"]
    for idx, user in enumerate(page_results, start=1 + page * PAGE_SIZE):
        lines.append(_format_user_card(idx, user, user_id))

    footer = f"\n<i>Sahifa {page+1}/{total_pages}</i>"
    reply_markup = search_results_keyboard(page, total_pages) if total_pages > 1 else main_menu_keyboard(user_id)

    sent = await message.answer(
        "".join(lines) + footer,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

    # Save search state for pagination
    if total_pages > 1:
        await state.update_data(
            search_skill=skill,
            search_results=[u["user_id"] for u in results],
            search_msg_id=sent.message_id,
        )


@router.callback_query(F.data.startswith("search_page:"))
async def cb_search_page(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    data = await state.get_data()
    skill = data.get("search_skill", "")
    result_ids = data.get("search_results", [])

    # Re-fetch users
    results = [storage.get_user(uid) for uid in result_ids if storage.get_user(uid)]
    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_results = results[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = [f"🔍 <b>\"{skill.title()}\" o'qituvchilari</b> — {len(results)} ta topildi\n\n"]
    for idx, user in enumerate(page_results, start=1 + page * PAGE_SIZE):
        lines.append(_format_user_card(idx, user, user_id))

    footer = f"\n<i>Sahifa {page+1}/{total_pages}</i>"
    await callback.message.edit_text(
        "".join(lines) + footer,
        parse_mode="HTML",
        reply_markup=search_results_keyboard(page, total_pages),
    )


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
