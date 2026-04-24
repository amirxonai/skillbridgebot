"""
keyboards/menu.py — Reusable keyboard markup builders (modernized).
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from skillbridge_bot.utils.i18n import _


def language_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard to pick the language."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🇺🇿 O'zbekcha"),
                KeyboardButton(text="🇷🇺 Русский"),
                KeyboardButton(text="🇬🇧 English"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Persistent bottom-bar keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_("menu_profile", user_id)),
                KeyboardButton(text=_("menu_search", user_id)),
            ],
            [
                KeyboardButton(text=_("menu_mentors", user_id)),
                KeyboardButton(text=_("menu_skills", user_id)),
            ],
            [
                KeyboardButton(text=_("menu_invite", user_id)),
                KeyboardButton(text=_("menu_help", user_id)),
            ],
            [
                KeyboardButton(
                    text=_("menu_webapp", user_id),
                    web_app=WebAppInfo(url="https://skillbridge.uz")
                ),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="...",
    )


def registration_type_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_("btn_exchange", user_id)),
                KeyboardButton(text=_("btn_mentor", user_id)),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=_("btn_cancel", user_id))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def rating_keyboard() -> InlineKeyboardMarkup:
    """Star rating keyboard (1–5)."""
    buttons = [
        InlineKeyboardButton(text=f"{'⭐' * i}", callback_data=f"rate:{i}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def profile_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Inline buttons shown under a profile card."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Ko'nikmalarni tahrirlash", callback_data="edit_skills"),
            InlineKeyboardButton(text="🔄 Yangi match", callback_data="find_match"),
        ],
        [
            InlineKeyboardButton(text="⭐ Sherikni baholash", callback_data="open_rate"),
            InlineKeyboardButton(text="🎓 Mentor bo'lish", callback_data="become_mentor"),
        ],
    ])


def mentor_detail_keyboard(mentor_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard under a mentor's profile card."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📨 Bog'lanish",
                url=f"tg://user?id={mentor_id}"
            ),
        ],
    ])


def mentors_nav_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination for mentors list."""
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"mentors_page:{page-1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"mentors_page:{page+1}"))
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="🔝 Asosiy menyu", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_results_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination for search results."""
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀️", callback_data=f"search_page:{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="▶️", callback_data=f"search_page:{page+1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="🎓 Mentorlar", callback_data="admin_mentors"),
            InlineKeyboardButton(text="⏳ Navbat", callback_data="admin_queue"),
        ],
        [
            InlineKeyboardButton(text="📢 E'lon yuborish", callback_data="admin_broadcast"),
        ],
    ])


def invite_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    """Share button for invite link."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Do'stlarga ulashish",
                url=f"https://t.me/share/url?url={invite_link}&text=SkillBridge%20-%20Bilim%20almashish%20platformasi!"
            )
        ],
        [
            InlineKeyboardButton(text="📊 Mening referallarim", callback_data="my_referrals"),
        ]
    ])
