# -*- coding: utf-8 -*-
"""
================================================================================
  🛰️ TeleHarvester Pro — The Autonomous Telegram Drop & Account Harvester
================================================================================
  Production Entrypoint & Service Runner
================================================================================
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Fix std streams when invoked via pythonw on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from telethon import events

from config.settings import AppConfig
from core.client import acquire_instance_lock, create_telegram_client
from core.engine import HarvestEngine
from utils.logger import setup_logger
from utils.storage import AlertStorage
from filters.precision_filter import inspect_and_filter_message

def run_filter_tests():
    """Runs built-in regression tests for the precision filter without connecting to Telegram."""
    print("=" * 60)
    print("🧪 Running TeleHarvester Filter Regression Suite...")
    print("=" * 60)

    test_cases = [
        ("ExpressVPN drop with combo", "XV-CHECK v10.0\nuser@example.com:secretPass123\nStatus: Active", True, "ExpressVPN Premium"),
        ("Canva team link drop", "انضم الآن إلى فريق كانفا برو مجاناً:\nhttps://www.canva.com/brand/join?token=abcd", True, "Canva Pro / Edu Team"),
        ("Spam begging question", "شكون عندو كود كانفا برو تعيشوا؟", False, None),
        ("Udemy spam course", "100% OFF coupon for python course on discudemy.com enroll now", False, None),
        ("Coursera Campus Drop", "Coursera campus invitation link:\nhttps://www.coursera.org/programs/free-program-123", True, "Coursera Plus / Campus"),
    ]

    passed = 0
    for name, text, expected_found, expected_cat in test_cases:
        res = inspect_and_filter_message(text, "TestChannel")
        if expected_found:
            if res and (expected_cat is None or res[0]['category'] == expected_cat):
                print(f"  ✅ PASS: {name} (Detected: {res[0]['category']})")
                passed += 1
            else:
                print(f"  ❌ FAIL: {name} (Expected {expected_cat}, got {res})")
        else:
            if res is None:
                print(f"  ✅ PASS: {name} (Correctly rejected)")
                passed += 1
            else:
                print(f"  ❌ FAIL: {name} (Expected rejection, but got: {res})")

    print("=" * 60)
    print(f"Result: {passed}/{len(test_cases)} tests passed.")
    print("=" * 60)
    return passed == len(test_cases)

async def run_harvester(config: AppConfig, logger):
    # Enforce single OS process lock
    _lock = acquire_instance_lock(config.lock_port)
    logger.info(f"Acquired instance lock on port {config.lock_port}")

    storage = AlertStorage(config.data_dir)
    client = create_telegram_client(config)
    engine = HarvestEngine(client, config, storage)

    backoff = 5
    while True:
        try:
            logger.info("Connecting to Telegram network...")
            async with client:
                if not await client.is_user_authorized():
                    logger.critical(
                        "❌ Client is not authorized! Please run with '--qr' to authenticate your account."
                    )
                    await asyncio.sleep(60)
                    continue

                me = await client.get_me()
                logger.info(f"✅ Authenticated as: {me.first_name} (@{me.username or 'NoUsername'}) [ID: {me.id}]")

                await engine.initialize()

                # Attach event listener
                @client.on(events.NewMessage)
                async def message_listener(event):
                    await engine.handle_new_message(event)

                logger.info("🚀 [TELEHARVESTER ACTIVE 24/7] Stream listening engaged...")
                while client.is_connected():
                    await asyncio.sleep(1)

            logger.warning("Disconnected from Telegram. Attempting reconnection...")
            backoff = 5
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Service manually stopped.")
            break
        except Exception as e:
            logger.exception(f"Connection loop exception ({e}). Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, config.max_reconnect_backoff)

def main():
    parser = argparse.ArgumentParser(description="TeleHarvester Pro — High-Speed Telegram Drop Harvester")
    parser.add_argument("--test", action="store_true", help="Run local filter unit tests")
    args = parser.parse_args()

    if args.test:
        success = run_filter_tests()
        sys.exit(0 if success else 1)

    config = AppConfig.from_env()
    logger = setup_logger(config.logs_dir, config.log_level)

    logger.info("==========================================================")
    logger.info("🛰️  TeleHarvester Pro — Starting Engine...")
    logger.info(f"• Log Level: {config.log_level}")
    logger.info(f"• Data Dir: {config.data_dir}")
    logger.info("==========================================================")

    if not config.api_id or not config.api_hash:
        logger.error(
            "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env file! "
            "Please copy .env.example to .env and configure your credentials."
        )
        sys.exit(1)

    try:
        asyncio.run(run_harvester(config, logger))
    except KeyboardInterrupt:
        logger.info("Exited.")

if __name__ == "__main__":
    main()
