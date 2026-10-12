# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — Centralized Configuration Engine
Loads environment variables and enforces typing and default fallbacks.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def load_dotenv_simple(env_path: Path):
    """Fallback .env parser if python-dotenv is not installed."""
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

# Load .env file
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        load_dotenv_simple(ENV_FILE)

@dataclass
class AppConfig:
    api_id: int
    api_hash: str
    phone_number: str
    session_name: str = "tele_harvester_session"
    
    # Destination Channels
    primary_channel_id: Optional[int] = None
    canva_channel_id: Optional[int] = None
    canva_topic_id: Optional[int] = None
    vpn_channel_id: Optional[int] = None
    ai_channel_id: Optional[int] = None
    
    # Operational
    lock_port: int = 58921
    max_reconnect_backoff: int = 60
    flood_sleep_threshold: int = 60
    enable_desktop_notifications: bool = True
    enable_local_json_logging: bool = True
    enable_local_markdown_logging: bool = True
    log_level: str = "INFO"
    
    # Directory paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"

    @classmethod
    def from_env(cls) -> "AppConfig":
        raw_api_id = os.getenv("TELEGRAM_API_ID", "0").strip()
        try:
            api_id = int(raw_api_id)
        except ValueError:
            api_id = 0

        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        phone_number = os.getenv("TELEGRAM_PHONE", "").strip()
        session_name = os.getenv("SESSION_NAME", "tele_harvester_session").strip()

        def parse_optional_int(key: str) -> Optional[int]:
            val = os.getenv(key, "").strip()
            if not val or val == "0":
                return None
            try:
                return int(val)
            except ValueError:
                return None

        cfg = cls(
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            session_name=session_name,
            primary_channel_id=parse_optional_int("PRIMARY_ALERT_CHANNEL_ID"),
            canva_channel_id=parse_optional_int("CANVA_ALERT_CHANNEL_ID"),
            canva_topic_id=parse_optional_int("CANVA_TOPIC_ID"),
            vpn_channel_id=parse_optional_int("VPN_ALERT_CHANNEL_ID"),
            ai_channel_id=parse_optional_int("AI_ALERT_CHANNEL_ID"),
            lock_port=int(os.getenv("LOCK_PORT", "58921")),
            max_reconnect_backoff=int(os.getenv("MAX_RECONNECT_BACKOFF_SECONDS", "60")),
            flood_sleep_threshold=int(os.getenv("FLOOD_SLEEP_THRESHOLD_SECONDS", "60")),
            enable_desktop_notifications=os.getenv("ENABLE_DESKTOP_NOTIFICATIONS", "true").lower() == "true",
            enable_local_json_logging=os.getenv("ENABLE_LOCAL_JSON_LOGGING", "true").lower() == "true",
            enable_local_markdown_logging=os.getenv("ENABLE_LOCAL_MARKDOWN_LOGGING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )
        
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        cfg.logs_dir.mkdir(parents=True, exist_ok=True)
        return cfg
