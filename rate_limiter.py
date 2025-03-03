
from datetime import datetime, timedelta
import threading
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests=100, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, client_id):
        now = datetime.now()
        with self.lock:
            # Remove old requests
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < timedelta(seconds=self.time_window)
            ]
            
            # Check if limit is exceeded
            if len(self.requests[client_id]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for client {client_id}")
                return False
            
            # Add new request
            self.requests[client_id].append(now)
            return True
