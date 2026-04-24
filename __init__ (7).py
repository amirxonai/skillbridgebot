"""
services/matcher.py — Smart Skill matching engine.

Matching Rules:
  - Perfect skill swap: A.learn == B.teach AND B.learn == A.teach
  - No duplicates: A and B must not be in each other's past_matches set.
  - Priority: Users with fewer matches_count are given priority to ensure
    fairness across the platform.
"""

from typing import Optional, Tuple, List
from skillbridge_bot.data import storage

def find_match(user_id: int) -> Optional[Tuple[int, int]]:
    """
    Search the waiting queue for the best candidate for user_id.
    Prioritises candidates with the lowest matches_count.

    Returns (user_id, candidate_id) if found, else None.
    """
    seeker = storage.get_user(user_id)
    if not seeker:
        return None

    queue = storage.get_queue()
    candidates = []

    for candidate_id in queue:
        if candidate_id == user_id:
            continue

        # Prevent matching exactly the same person again
        if storage.have_matched_before(user_id, candidate_id):
            continue

        candidate = storage.get_user(candidate_id)
        if not candidate:
            continue

        # Check bidirectional swap
        if (seeker["learn_skill"] == candidate["teach_skill"] and
            candidate["learn_skill"] == seeker["teach_skill"]):
            candidates.append(candidate)

    if not candidates:
        return None

    # Sort candidates by the fewest historical matches to prioritize newcomers
    candidates.sort(key=lambda c: c["matches_count"])
    best_candidate = candidates[0]

    return (user_id, best_candidate["user_id"])


def run_matching_for_queue() -> List[Tuple[int, int]]:
    """
    Scan the entire waiting queue and return all possible new matched pairs.
    Users with fewer matches are prioritised.

    Returns:
        List of tuples (user_a, user_b).
    """
    matched_pairs = []
    already_matched = set()

    # Get the queue and order it by 'matches_count' ascending, so low-match users go first
    queue_uids = storage.get_queue()
    users_in_queue = []

    for uid in queue_uids:
        u = storage.get_user(uid)
        if u:
            users_in_queue.append(u)

    # Sort queue users by matches count so that users with fewest matches get processed first
    users_in_queue.sort(key=lambda x: x["matches_count"])

    for i, user_a in enumerate(users_in_queue):
        uid_a = user_a["user_id"]
        if uid_a in already_matched:
            continue

        # Try to find a match among all remaining users in queue
        for user_b in users_in_queue[i+1:]:
            uid_b = user_b["user_id"]
            if uid_b in already_matched:
                continue

            # Prevent duplicate matches history
            if storage.have_matched_before(uid_a, uid_b):
                continue

            if (user_a["learn_skill"] == user_b["teach_skill"] and
                user_b["learn_skill"] == user_a["teach_skill"]):

                matched_pairs.append((uid_a, uid_b))
                already_matched.add(uid_a)
                already_matched.add(uid_b)
                break  # match found for A, go to next person

    return matched_pairs


def search_teachers(skill: str) -> List[dict]:
    """Find users who teach the given skill."""
    skill_lower = skill.strip().lower()
    return [u for u in storage.get_all_users() if skill_lower in u["teach_skill"]]
