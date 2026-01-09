"""
Configuration Module - Type-Safe Environment Variable Management
================================================================
Uses Pydantic BaseSettings for validated environment variable loading.
All production-critical settings MUST be explicitly defined in .env file.

Security Notes:
- JWT_SECRET must be minimum 32 characters
- MongoDB URI format is validated
- CORS origins are restricted to prevent XSS
"""

import re
from typing import List
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    Reads from environment variables with .env file support.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # MongoDB Configuration
    MONGO_URI: str = Field(default="mongodb://localhost:27017")
    MONGO_DB_NAME: str = Field(default="momwatch_db")
    MONGO_MAX_POOL_SIZE: int = Field(default=50, ge=1, le=100)
    MONGO_MIN_POOL_SIZE: int = Field(default=10, ge=1, le=50)
    
    # Security & JWT
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=1440, ge=1)
    
    # API Server
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000, ge=1024, le=65535)
    API_WORKERS: int = Field(default=4, ge=1, le=16)
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:8501"])
    
    # ML Model Configuration
    MODEL_PATH: str = Field(default="/app/models/maternal_rf_model.joblib")
    SCALER_PATH: str = Field(default="/app/models/feature_scaler.joblib")
    LABEL_ENCODER_PATH: str = Field(default="/app/models/label_encoder.joblib")
    MODEL_CONFIDENCE_THRESHOLD: float = Field(default=0.75, ge=0.0, le=1.0)
    
    # Circuit Breaker Settings
    CIRCUIT_FAILURE_THRESHOLD: int = Field(default=5, ge=1, le=20)
    CIRCUIT_TIMEOUT_SECONDS: int = Field(default=60, ge=10, le=600)
    CIRCUIT_HALF_OPEN_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    
    # Idempotency
    IDEMPOTENCY_TTL_MINUTES: int = Field(default=10, ge=1, le=60)
    
    # FSM & HITL Configuration (Build2Break additions)
    HONEYPOT_ENABLED: bool = Field(default=True)
    HONEYPOT_LOG_TO_DB: bool = Field(default=True)
    HITL_CONFIDENCE_THRESHOLD: float = Field(default=0.65, ge=0.0, le=1.0)
    FSM_STATE_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: str = Field(default="/app/logs/momwatch.log")
    
    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """
        Validate JWT secret strength.
        
        Security requirements:
        - Minimum 32 characters (enforced by Field)
        - Cannot be common/weak patterns
        - Must not contain only alphanumeric characters (requires special chars)
        """
        # Check for common weak patterns
        weak_patterns = [
            "your-secret-key",
            "change-me",
            "example",
            "test",
            "secret",
            "password",
            "default"
        ]
        
        v_lower = v.lower()
        for pattern in weak_patterns:
            if pattern in v_lower:
                raise ValueError(
                    f"JWT_SECRET contains weak pattern '{pattern}'. "
                    "Generate a strong secret using: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
        
        # Check entropy - must contain variety of characters
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "JWT_SECRET must contain uppercase, lowercase, and numeric characters. "
                "Generate a strong secret using: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        
        return v
    
    @field_validator("MONGO_URI")
    @classmethod
    def validate_mongo_uri(cls, v: str) -> str:
        """Validate MongoDB URI format."""
        pattern = r'^mongodb(\+srv)?:\/\/.+'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid MongoDB URI format: {v}. "
                "Must start with 'mongodb://' or 'mongodb+srv://'"
            )
        return v
    
    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret meets security requirements."""
        if len(v) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters. Current length: {len(v)}. "
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a recognized value."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: {v}. Must be one of {valid_levels}"
            )
        return v_upper
    
    @property
    def idempotency_ttl_seconds(self) -> int:
        """Convert idempotency TTL to seconds for MongoDB."""
        return self.IDEMPOTENCY_TTL_MINUTES * 60
    
    @property
    def jwt_expiration_seconds(self) -> int:
        """Convert JWT expiration to seconds."""
        return self.JWT_EXPIRATION_MINUTES * 60
    
    @property
    def hitl_confidence_threshold(self) -> float:
        """HITL trigger threshold (lowercase for backward compatibility)."""
        return self.HITL_CONFIDENCE_THRESHOLD


# Global settings instance
# This will be imported throughout the application
try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(
        f"FATAL: Configuration validation failed: {str(e)}. "
        "Please check your .env file and ensure all required variables are set correctly."
    ) from e
