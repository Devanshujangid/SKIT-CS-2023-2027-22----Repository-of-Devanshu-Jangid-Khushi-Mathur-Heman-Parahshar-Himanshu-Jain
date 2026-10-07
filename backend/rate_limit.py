import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException


RATE_LIMIT_REQUESTS = int(
    os.getenv("GEMINI_RATE_LIMIT_REQUESTS", "5")
)

RATE_LIMIT_WINDOW = int(
    os.getenv("GEMINI_RATE_LIMIT_WINDOW", "60")
)

_requests = defaultdict(deque)


def check_gemini_rate_limit(user_id: str):
    now = time.time()
    request_times = _requests[user_id]

    while request_times and now - request_times[0] >= RATE_LIMIT_WINDOW:
        request_times.popleft()

    if len(request_times) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "message": "Too many AI generation requests. Please try again later."
            }
        )

    request_times.append(now)