# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — Client Connection & Collision Guard
Controls Telethon lifecycle, instance locking, and reconnect loops.
"""

import sys
import socket
import logging
import asyncio
from pathlib import Path
from telethon import TelegramClient

from config.settings import AppConfig

logger = logging.getLogger("TeleHarvester.Client")

def acquire_instance_lock(port: int) -> socket.socket:
    """Enforces a single running instance across the OS via TCP port binding."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
        s.listen(1)
        return s
    except socket.error:
        logger.critical(
            f"❌ Another instance of TeleHarvester is already running on port {port}. "
            "Terminating this process to avoid session lock conflicts."
        )
        sys.exit(0)

def create_telegram_client(config: AppConfig) -> TelegramClient:
    """Instantiates the Telethon client with configured session storage."""
    session_path = config.data_dir / config.session_name
    client = TelegramClient(
        str(session_path),
        config.api_id,
        config.api_hash
    )
    client.flood_sleep_threshold = config.flood_sleep_threshold
    return client
