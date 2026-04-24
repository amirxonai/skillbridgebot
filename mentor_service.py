"""
handlers/start.py — Registration flow handler.

Includes the new `user_type` question (Exchange vs Mentor seekers).
"""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

from skillbridge_bot.data import storage
from skillbridge_bot.keyboards.menu import main_menu_keyboard, cancel_keyboard, registration_type_keyboard, language_keyboard
from skillbridge_bot.services import matcher
from skillbridge_bot.utils.i18n import _

router = Router()

class Registration(StatesGroup):
    language = State()
    teach_skill = State()
    learn_skill = State()
    user_type = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandStart = None) -> None:
    user_id = message.from_user.id
    
    # Check for referral payload
    if command and command.args and command.args.startswith("ref_"):
        try:
            invited_by = int(command.args.replace("ref_", ""))
            # Don't let users invite themselves
            if invited_by != user_id:
                await state.update_data(invited_by=invited_by)
        except (ValueError, TypeError):
            pass

    if storage.user_exists(user_id):
        user = storage.get_user(user_id)
        await message.answer(
            _("welcome_back", user_id, username=user['username']),
            reply_markup=main_menu_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    # Check language
    if not storage.get_user_language(user_id):
        await message.answer(
            _("choose_language", user_id),
            reply_markup=language_keyboard(),
        )
        await state.set_state(Registration.language)
        return

    # If language exists but user not registered (e.g., they canceled registration), start over
    await start_registration_flow(message, state, user_id)


@router.message(Registration.language)
async def process_language(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Map button text to language code
    if "O'zbekcha" in text:
        lang_code = "uz"
    elif "Русский" in text:
        lang_code = "ru"
    elif "English" in text:
        lang_code = "en"
    else:
        # Default fallback if they typed something weird
        lang_code = "uz"

    storage.set_user_language(user_id, lang_code)
    await message.answer(
        _("language_set", user_id),
        reply_markup=ReplyKeyboardRemove(),
    )
    await start_registration_flow(message, state, user_id)


async def start_registration_flow(message: Message, state: FSMContext, user_id: int):
    await message.answer(
        _("welcome_unregistered", user_id),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )

    await message.answer(
        _("ask_teach_skill", user_id),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(Registration.teach_skill)


# Catch accidental commands during FSM
@router.message(Registration.teach_skill, F.text.startswith('/'))
@router.message(Registration.learn_skill, F.text.startswith('/'))
@router.message(Registration.user_type, F.text.startswith('/'))
async def fallback_commands_in_fsm(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer(_("registration_cancelled", user_id), reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(_("finish_registration_first", user_id))

@router.message(Registration.teach_skill)
async def process_teach_skill(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    if text.lower() in ("❌ cancel", "❌ bekor qilish", "❌ отмена"):
        await state.clear()
        await message.answer(_("registration_cancelled", user_id), reply_markup=ReplyKeyboardRemove())
        return

    if len(text) < 2:
        await message.answer(_("enter_real_skill", user_id))
        return

    await state.update_data(teach_skill=text)
    await message.answer(
        _("ask_learn_skill", user_id, teach_skill=text),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(user_id),
    )
    await state.set_state(Registration.learn_skill)


@router.message(Registration.learn_skill)
async def process_learn_skill(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    if text.lower() in ("❌ cancel", "❌ bekor qilish", "❌ отмена"):
        await state.clear()
        await message.answer(_("registration_cancelled", user_id), reply_markup=ReplyKeyboardRemove())
        return

    if len(text) < 2:
        await message.answer(_("enter_real_skill", user_id))
        return

    await state.update_data(learn_skill=text)
    await message.answer(
        _("ask_role", user_id, learn_skill=text),
        parse_mode="HTML",
        reply_markup=registration_type_keyboard(user_id),
    )
    await state.set_state(Registration.user_type)


@router.message(Registration.user_type)
async def process_user_type(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = message.text.strip()
    if text.lower() in ("❌ cancel", "/cancel", "❌ bekor qilish", "❌ отмена"):
        await state.clear()
        await message.answer(_("registration_cancelled", user_id), reply_markup=ReplyKeyboardRemove())
        return

    # Map raw button text to internal roles
    role = "exchange"
    if "mentor" in text.lower():
        role = "learner"

    data = await state.get_data()
    teach_skill = data["teach_skill"]
    learn_skill = data["learn_skill"]
    invited_by  = data.get("invited_by")

    username = message.from_user.username or message.from_user.first_name or f"user_{user_id}"

    # Push to database
    storage.create_user(user_id, username, teach_skill, learn_skill, user_type=role, invited_by=invited_by)
    await state.clear()

    await message.answer(
        _("registration_complete", user_id, username=username, teach_skill=teach_skill, learn_skill=learn_skill, role=role.title()),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user_id),
    )

    # Attempt instant match
    match_result = matcher.find_match(user_id)
    if match_result:
        uid_a, uid_b = match_result
        partner_id = uid_b if uid_a == user_id else uid_a
        partner = storage.get_user(partner_id)

        storage.remove_from_queue(uid_a)
        storage.remove_from_queue(uid_b)
        storage.add_match(uid_a, uid_b)

        await message.answer(
            _("match_found", user_id, partner_username=partner['username'], partner_teach=partner['teach_skill'], partner_learn=partner['learn_skill']),
            parse_mode="HTML",
        )

        try:
            current_user = storage.get_user(user_id)
            await message.bot.send_message(
                partner_id,
                _("match_found", partner_id, partner_username=current_user['username'], partner_teach=current_user['teach_skill'], partner_learn=current_user['learn_skill']),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        # User gets pushed to queue
        storage.add_to_queue(user_id)
        await message.answer(
            _("added_to_queue", user_id),
            parse_mode="HTML",
        )

@router.message(Command("help"))
@router.message(F.text.in_({"❓ Help", "❓ Yordam", "❓ Помощь"}))
async def cmd_help(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer(
        _("cmd_help", user_id),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user_id),
    )
