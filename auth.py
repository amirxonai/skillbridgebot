"""
services/mentor_service.py — Mentor aggregation and querying logic.
"""

from typing import List, Dict, Any
from skillbridge_bot.data import storage

def get_top_mentors(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve users with user_type "mentor", ordered by rating descending.
    """
    users = storage.get_all_users()
    mentors = [u for u in users if u.get("user_type") == "mentor"]
    
    # Sort descending by rating, fallback to matches count
    mentors.sort(key=lambda m: (m.get("rating", 0.0), m.get("matches_count", 0)), reverse=True)
    return mentors[:limit]

def get_skill_categories() -> Dict[str, int]:
    """
    Aggregates all taught skills into communities.
    Returns a dict mapping the skill name to the number of teachers.
    E.g. {"python": 5, "design": 2}
    """
    users = storage.get_all_users()
    categories = {}
    
    for u in users:
        skill = u.get("teach_skill")
        if skill:
            categories[skill] = categories.get(skill, 0) + 1
            
    # Sort by popularity descending
    sorted_categories = dict(sorted(categories.items(), key=lambda item: item[1], reverse=True))
    return sorted_categories
