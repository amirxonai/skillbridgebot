"""
handlers/rating.py — /rate command handlers.

Allows users to rate the partner they are currently matched with.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import main_menu_keyboard, rating_keyboard
from skillbridge_bot.config import MIN_RATING, MAX_RATING
from skillbridge_bot.utils.i18n import _
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()

class RatingStates(StatesGroup):
    wait_for_comment = State()

@router.message(Command("rate"))
@router.message(F.text.in_({"⭐ Rate Match", "⭐ Sherikni baholash", "⭐ Оценить партнера"}))
async def cmd_rate(message: Message) -> None:
    """Initiate the rating flow for an active match."""
    user_id = message.from_user.id

    if not storage.user_exists(user_id):
        await message.answer(_("rate_unregistered", user_id))
        return

    match_id = storage.get_match(user_id)
    if match_id is None:
        await message.answer(
            _("rate_no_match", user_id),
            reply_markup=main_menu_keyboard(user_id),
        )
        return

    partner = storage.get_user(match_id)
    if not partner:
        await message.answer(_("rate_partner_not_found", user_id))
        return

    # Record who this user intends to rate
    storage.set_pending_rating(user_id, match_id)

    await message.answer(
        _("rate_prompt", user_id, partner_name=partner['username']),
        parse_mode="HTML",
        reply_markup=rating_keyboard(),
    )


@router.callback_query(F.data.startswith("rate:"))
async def process_rating(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle the inline keyboard star-rating callback."""
    rater_id = callback.from_user.id

    # Validate that they have a pending rating.
    target_id = storage.get_pending_rating(rater_id)
    if target_id is None:
        await callback.answer(_("rate_no_pending", rater_id), show_alert=True)
        return

    # Parse the score
    try:
        score = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(_("rate_invalid_format", rater_id), show_alert=True)
        return

    if not (MIN_RATING <= score <= MAX_RATING):
        await callback.answer(_("rate_out_of_bounds", rater_id, min_r=MIN_RATING, max_r=MAX_RATING), show_alert=True)
        return

    partner = storage.get_user(target_id)
    partner_name = partner["username"] if partner else "Unknown"

    # Remove the pending flag (we'll save score now, but we check pending for comments too)
    # Actually, let's keep intended target in state, and storage pending as a backup
    await state.update_data(rating_target_id=target_id, rating_score=score)
    
    await callback.answer(_("rate_toast", rater_id, partner_name=partner_name, score=score), show_alert=False)

    stars_display = "⭐" * score + "☆" * (MAX_RATING - score)
    await callback.message.edit_text(
        _("rate_submitted", rater_id, partner_name=partner_name, stars_display=stars_display, score=score, max_r=MAX_RATING),
        parse_mode="HTML",
    )
    
    await callback.message.answer(
        _("rate_ask_comment", rater_id),
        parse_mode="HTML"
    )
    await state.set_state(RatingStates.wait_for_comment)

@router.message(RatingStates.wait_for_comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    data = await state.get_data()
    
    target_id = data.get("rating_target_id")
    score     = data.get("rating_score")
    
    if not target_id or not score:
        # Fallback to storage if state evaporated
        target_id = storage.get_pending_rating(user_id)
        # If still none, something is wrong
        if not target_id:
            await state.clear()
            return

    comment = None
    if text.lower() not in ("skip", "o'tkazish", "пропустить", "/skip"):
        comment = text

    # Final save to database
    storage.add_rating(user_id, target_id, score, comment)
    storage.clear_pending_rating(user_id)
    
    await state.clear()
    await message.answer(
        _("rate_comment_received", user_id),
        reply_markup=main_menu_keyboard(user_id),
        parse_mode="HTML"
    )
