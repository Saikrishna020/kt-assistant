"""Rate limiting and request throttling for API calls."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting and retry behavior."""

    requests_per_minute: int = 60  # Free tier: ~60 req/min
    request_delay_ms: int = 1000  # Minimum delay between requests (ms)
    max_retries: int = 3  # Max retry attempts
    base_retry_delay_ms: int = 1000  # Initial retry delay (exponential backoff)
    max_retry_delay_ms: int = 30000  # Cap on retry delay
    timeout_seconds: int = 90  # API request timeout


class RateLimiter:
    """
    Rate limiter with request queuing and exponential backoff retry logic.
    
    Prevents 429 errors by:
    1. Enforcing minimum delay between requests
    2. Limiting requests per minute
    3. Retrying failed requests with exponential backoff
    4. Graceful queue management
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self.last_request_time: float = 0.0
        self.request_times: list[float] = []
        self.min_delay_seconds = self.config.request_delay_ms / 1000.0

    def _clean_old_times(self) -> None:
        """Remove request times older than 1 minute."""
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]

    def wait_if_needed(self) -> None:
        """
        Wait if necessary to respect rate limits.
        
        Checks:
        1. Minimum delay between requests
        2. Requests per minute limit
        """
        self._clean_old_times()

        # Check minimum delay since last request
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_delay_seconds:
            sleep_time = self.min_delay_seconds - time_since_last
            time.sleep(sleep_time)

        # Check requests per minute limit
        now = time.time()
        if len(self.request_times) >= self.config.requests_per_minute:
            oldest_time = self.request_times[0]
            time_until_window_clear = 60 - (now - oldest_time)
            if time_until_window_clear > 0:
                time.sleep(time_until_window_clear)
                self._clean_old_times()

        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)

    def calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for retry.
        
        Formula: base_delay * (2 ^ attempt) with jitter and cap
        """
        delay_ms = min(
            self.config.base_retry_delay_ms * (2 ** attempt),
            self.config.max_retry_delay_ms,
        )
        # Add small jitter (±10%) to prevent thundering herd
        jitter = delay_ms * 0.1 * (2 * (time.time() % 1) - 1)
        return (delay_ms + jitter) / 1000.0

    def is_retryable_error(self, error_code: int | None) -> bool:
        """Check if error is worth retrying."""
        if error_code is None:
            return False
        # Retry on: 429 (rate limit), 500-599 (server errors), 408 (timeout)
        return error_code == 429 or error_code == 408 or (500 <= error_code < 600)

    def execute_with_retries(
        self,
        func: Callable[[], T],
        operation_name: str = "API request",
    ) -> T:
        """
        Execute function with rate limiting and retry logic.
        
        Args:
            func: Callable that returns result or raises RuntimeError with error code
            operation_name: Description for logging
            
        Returns:
            Result from func on success
            
        Raises:
            RuntimeError: If all retries exhausted
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Rate limit before each attempt
                self.wait_if_needed()

                # Execute the function
                return func()

            except RuntimeError as exc:
                last_exception = exc
                error_msg = str(exc)

                # Check if error code is in message (from GeminiClient)
                error_code = None
                if "HTTP error" in error_msg:
                    try:
                        code_str = error_msg.split("HTTP error ")[1].split(":")[0]
                        error_code = int(code_str)
                    except (IndexError, ValueError):
                        pass

                # Check if retryable
                if not self.is_retryable_error(error_code) or attempt >= self.config.max_retries:
                    raise

                # Calculate backoff and wait
                backoff = self.calculate_backoff_delay(attempt)
                print(f"⏳ {operation_name} failed (attempt {attempt + 1}/{self.config.max_retries + 1}). "
                      f"Retrying in {backoff:.1f}s... (error: HTTP {error_code})")
                time.sleep(backoff)

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed to execute {operation_name} after {self.config.max_retries + 1} attempts")
