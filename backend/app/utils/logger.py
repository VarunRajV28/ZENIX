"""
Centralized Logging Configuration
==================================
Provides structured logging with file rotation and JSON formatting.
All application logs are centralized for audit trails.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context fields.
    """
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName


def setup_logger(name: str = "momwatch") -> logging.Logger:
    """
    Configure logger with console and file handlers.
    
    Args:
        name: Logger name (default: "momwatch")
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Prevent duplicate handlers if already configured
    if logger.handlers:
        return logger
    
    # Console Handler (Human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File Handler (JSON format for structured logging)
    log_path = Path(settings.LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        settings.LOG_FILE_PATH,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    file_handler.setFormatter(json_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger()


def log_request(endpoint: str, user_id: str, status: str, duration_ms: int):
    """
    Log API request with structured data.
    
    Args:
        endpoint: API endpoint path
        user_id: User identifier
        status: Response status (success/error)
        duration_ms: Request processing time in milliseconds
    """
    logger.info(
        "API Request",
        extra={
            "endpoint": endpoint,
            "user_id": user_id,
            "status": status,
            "duration_ms": duration_ms
        }
    )


def log_circuit_breaker(state: str, reason: str):
    """
    Log circuit breaker state transitions.
    
    Args:
        state: New circuit breaker state (OPEN/CLOSED/HALF_OPEN)
        reason: Reason for state transition
    """
    logger.warning(
        f"Circuit Breaker: {state}",
        extra={
            "circuit_state": state,
            "reason": reason
        }
    )


def log_security_event(event_type: str, user_id: str, details: dict):
    """
    Log security-related events for audit trail.
    
    Args:
        event_type: Type of security event (login_failed, token_invalid, etc.)
        user_id: User identifier
        details: Additional event details
    """
    logger.warning(
        f"Security Event: {event_type}",
        extra={
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        }
    )
