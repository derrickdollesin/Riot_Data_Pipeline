import time
from collections import deque


class RateLimiter:
    """
    Sliding-window rate limiter supporting multiple concurrent rate limits.

    Each rate is represented as:
        (max_requests, window_seconds)

    Example:
        [(20, 1), (100, 120)]

    A request is permitted only when it satisfies every configured
    rate limit.
    """

    def __init__(self, rates: list):
        # Chronological history of successful request timestamps.
        self.request_timestamps = deque()
        self.rates = rates

    def acquire(self):
        """
        Block until a request can be made without exceeding any
        configured rate limit.
        """

        # Retry after sleeping whenever one or more limits are reached.
        while True:
            current_time = time.monotonic()

            # Discard timestamps older than the largest configured window.
            # These requests can no longer contribute to any rate limit.
            longest_window = max([rate[1] for rate in self.rates])
            cleanup_boundary = current_time - longest_window

            while (
                self.request_timestamps
                and self.request_timestamps[0] < cleanup_boundary
            ):
                self.request_timestamps.popleft()

            # Track the longest wait required across all configured limits.
            # The request can proceed only after every limit is satisfied.
            required_wait = 0

            for rate in self.rates:
                max_requests = rate[0]
                window_seconds = rate[1]

                window_boundary = current_time - window_seconds

                # Count requests still active within the current sliding
                # window and determine when the oldest one expires.
                requests_in_window = 0

                for timestamp in self.request_timestamps:
                    if timestamp > window_boundary:
                        if not requests_in_window:
                            oldest_request_expiration = (
                                timestamp + window_seconds
                            )

                        requests_in_window += 1

                # This rate has remaining capacity and does not require
                # the caller to wait.
                if requests_in_window < max_requests:
                    continue

                # The window is at capacity. Determine when its oldest
                # active request expires and capacity becomes available.
                window_wait = oldest_request_expiration - current_time

                if window_wait > required_wait:
                    required_wait = window_wait

            if required_wait == 0:
                # All configured limits have capacity. Record the request
                # before returning so subsequent calls account for it.
                self.request_timestamps.append(current_time)
                print(current_time)
                return
            else:
                # At least one limit is at capacity. Wait for the most
                # restrictive window, then reevaluate all limits.
                time.sleep(required_wait)