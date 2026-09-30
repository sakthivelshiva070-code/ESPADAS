import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-please-0123456789")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me-please-0123456789")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", "8")))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///learnadapt.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # AI generation layer (blank key -> offline demo generator)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-5-5")
    AI_MAX_REGENERATIONS = 2

    # Closed loop: create the next adaptation automatically after each submission
    AUTO_ADAPT = os.getenv("AUTO_ADAPT", "true").lower() == "true"

    # Adaptation engine thresholds (blueprint section 13: "can be configurable")
    ADAPT = {
        "accuracy_significant": 50,   # < 50  -> significant support
        "accuracy_moderate": 75,      # 50-74 -> moderate support
        "accuracy_challenge": 85,     # >= 85 -> consider more challenge
        "completion_low": 60,         # < 60% completion -> shorter activity
        "response_time_high": 60,     # avg seconds per question considered "high"
        "trend_delta": 3,             # mastery change needed to call a trend
        "min_questions": 3,
        "max_questions": 20,
        "repeated_error_min": 2,      # same error tag this many times = repeated
        "mastery_alpha": 0.6,         # weight of newest accuracy in mastery update
        "attention_mastery": 50,      # below this -> needs teacher attention
    }
