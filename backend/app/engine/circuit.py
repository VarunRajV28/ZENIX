"""
Circuit Breaker Pattern - Prevent Cascading Failures
=====================================================
Implements 3-state circuit breaker (CLOSED/OPEN/HALF_OPEN) to protect
against ML model failures and prevent cascading system failures.

States:
- CLOSED: Normal operation, all requests pass to ML model
- OPEN: ML model bypassed after threshold failures, only rules engine used
- HALF_OPEN: Testing recovery, limited requests to ML

State Transitions:
- CLOSED → OPEN: After CIRCUIT_FAILURE_THRESHOLD consecutive failures
- OPEN → HALF_OPEN: After CIRCUIT_TIMEOUT_SECONDS cooldown
- HALF_OPEN → CLOSED: After CIRCUIT_HALF_OPEN_ATTEMPTS successful calls
- HALF_OPEN → OPEN: On any failure during test window
"""

import time
from typing import Callable, Any
from enum import Enum
from app.config import settings
from app.utils.logger import logger, log_circuit_breaker


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for ML model protection.
    
    Tracks failure count and automatically opens circuit when threshold
    exceeded, preventing cascading failures.
    """
    
    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0
        self.failure_threshold = settings.CIRCUIT_FAILURE_THRESHOLD
        self.timeout_seconds = settings.CIRCUIT_TIMEOUT_SECONDS
        self.half_open_attempts = settings.CIRCUIT_HALF_OPEN_ATTEMPTS
        
        logger.info(
            f"Circuit Breaker initialized: threshold={self.failure_threshold}, "
            f"timeout={self.timeout_seconds}s"
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result if successful
        
        Raises:
            CircuitBreakerOpen: If circuit is OPEN
            Exception: If function execution fails
        """
        # Check if circuit should transition to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is OPEN. ML model unavailable. "
                    f"Cooldown remaining: {int(self.timeout_seconds - (time.time() - self.last_failure_time))}s. "
                    f"Using fallback to clinical rules engine."
                )
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """
        Handle successful execution.
        """
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker HALF_OPEN: Success {self.success_count}/{self.half_open_attempts}"
            )
            
            # Transition to CLOSED after required successes
            if self.success_count >= self.half_open_attempts:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(f"Circuit breaker: Failure count reset (was {self.failure_count})")
                self.failure_count = 0
    
    def _on_failure(self) -> None:
        """
        Handle failed execution.
        """
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(
            f"Circuit breaker failure: {self.failure_count}/{self.failure_threshold}",
            extra={"state": self.state.value, "failure_count": self.failure_count}
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # Immediate transition to OPEN on failure during test
            self._transition_to_open("Failure during HALF_OPEN test")
        
        elif self.state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open(f"Failure threshold exceeded ({self.failure_count} failures)")
    
    def _transition_to_open(self, reason: str) -> None:
        """
        Transition to OPEN state.
        """
        self.state = CircuitState.OPEN
        self.success_count = 0
        log_circuit_breaker("OPEN", reason)
        logger.warning(
            f"⚠️ Circuit breaker OPENED: {reason}. "
            f"ML model will be bypassed for {self.timeout_seconds}s. "
            "System will use clinical rules engine as fallback."
        )
    
    def _transition_to_half_open(self) -> None:
        """
        Transition to HALF_OPEN state.
        """
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        log_circuit_breaker("HALF_OPEN", "Cooldown period expired, testing recovery")
        logger.info(
            f"Circuit breaker → HALF_OPEN: Testing ML model recovery "
            f"(need {self.half_open_attempts} successes)"
        )
    
    def _transition_to_closed(self) -> None:
        """
        Transition to CLOSED state.
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        log_circuit_breaker("CLOSED", f"Recovery successful ({self.half_open_attempts} consecutive successes)")
        logger.info(
            "✓ Circuit breaker → CLOSED: ML model recovered successfully. "
            "Normal operation resumed."
        )
    
    def get_status(self) -> dict:
        """
        Get circuit breaker status.
        
        Returns:
            Dictionary with current state and metrics
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout_seconds,
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time > 0 else 0
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
