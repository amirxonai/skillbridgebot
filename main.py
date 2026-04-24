"""
services/queue.py — Background matching engine.

Periodically scans the waiting queue to detect new skill matches.
When a match is found, removes users from the queue and sends them a notification.
"""

import asyncio
import logging
from aiogram import Bot

from skillbridge_bot.data import storage
from skillbridge_bot.services import matcher
from skillbridge_bot.utils.i18n import _

logger = logging.getLogger(__name__)


async def start_queue_worker(bot: Bot, interval_seconds: int = 15) -> None:
    """
    Run a background loop that periodically calls the match engine
    and notifies matched users.
    """
    logger.info("Background queue worker started. Checking every %s seconds...", interval_seconds)
    
    while True:
        try:
            # Sleep first so we don't spam checks instantly
            await asyncio.sleep(interval_seconds)
            
            # Find all possible matches in the queue right now
            new_matches = matcher.run_matching_for_queue()
            
            for uid_a, uid_b in new_matches:
                # 1. Update the in-memory data store
                storage.add_match(uid_a, uid_b)
                storage.remove_from_queue(uid_a)
                storage.remove_from_queue(uid_b)
                
                # 2. Extract user info
                user_a = storage.get_user(uid_a)
                user_b = storage.get_user(uid_b)
                
                # If a user evaporated somehow, skip them
                if not user_a or not user_b:
                    continue

                username_a = user_a["username"]
                username_b = user_b["username"]
                
                # 3. Message BOTH users about their new match
                msg_a = (
                    f"🎉 <b>Match Found!</b>\n\n"
                    f"You can exchange skills with <b>@{username_b}</b>\n\n"
                    f"📚 They teach: <b>{user_b['teach_skill']}</b>\n"
                    f"🎯 They learn: <b>{user_b['learn_skill']}</b>\n\n"
                    "Reach out to them and start learning! 🚀"
                )
                msg_b = (
                    f"🎉 <b>Match Found!</b>\n\n"
                    f"You can exchange skills with <b>@{username_a}</b>\n\n"
                    f"📚 They teach: <b>{user_a['teach_skill']}</b>\n"
                    f"🎯 They learn: <b>{user_a['learn_skill']}</b>\n\n"
                    "Reach out to them and start learning! 🚀"
                )
                
                # We use try/except block to ignore users who blocked the bot
                try:
                    await bot.send_message(uid_a, msg_a, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Could not notify {uid_a}: {e}")
                    
                try:
                    await bot.send_message(uid_b, msg_b, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Could not notify {uid_b}: {e}")
                    
                logger.info(f"✨ Auto-matched pair: {uid_a} <-> {uid_b}")

        except asyncio.CancelledError:
            # Break cleanly on shutdown
            break
        except Exception as e:
            # Catch all other exceptions so the loop NEVER dies
            logger.error(f"Error in background queue loop: {e}", exc_info=True)

async def start_followup_worker(bot: Bot, interval_seconds: int = 3600) -> None:
    """
    Periodically check for matches that happened 24 hours ago 
    and send a follow-up message to both users.
    """
    logger.info("Follow-up worker started. Checking every hour...")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            # 1. Get matches that need follow-up (default 24h)
            pending_matches = storage.get_matches_for_followup(hours_ago=24)
            
            for match in pending_matches:
                # Notify BOTH users
                uids = [match.user_a_id, match.user_b_id]
                
                for i, uid in enumerate(uids):
                    partner_id = uids[1-i]
                    partner = storage.get_user(partner_id)
                    
                    if partner:
                        msg = _("follow_up_msg", uid, partner_name=partner['username'])
                        try:
                            await bot.send_message(uid, msg, parse_mode="HTML")
                        except Exception:
                            pass
                
                # Mark as handled
                storage.mark_followed_up(match.id)
                logger.info(f"📬 Sent follow-up for match #{match.id}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in follow-up worker: {e}", exc_info=True)
