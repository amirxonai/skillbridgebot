"""Rate limiting middleware for FastAPI."""
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "default": "100/minute",          # 100 requests per minute
    "register": "5/minute",            # 5 registrations per minute
    "search": "30/minute",             # 30 searches per minute
    "api_admin": "10/minute",          # 10 admin calls per minute
}

def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Custom error response for rate limiting."""
    return {
        "detail": "Too many requests. Please try again later.",
        "retry_after": exc.detail if hasattr(exc, 'detail') else "60"
    }
