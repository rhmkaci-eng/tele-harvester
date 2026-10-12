# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — Real-time Event Processing Engine
Listens to incoming Telegram streams, runs heuristic filters, and routes alerts.
"""

import logging
import asyncio
from typing import Optional, Set
from datetime import datetime, timezone
from telethon import TelegramClient, events

from config.settings import AppConfig
from filters.precision_filter import inspect_and_filter_message
from utils.storage import AlertStorage
from core.notifier import format_telegram_alert, notify_desktop

logger = logging.getLogger("TeleHarvester.Engine")

class HarvestEngine:
    def __init__(self, client: TelegramClient, config: AppConfig, storage: AlertStorage):
        self.client = client
        self.config = config
        self.storage = storage
        self.ignored_chat_ids: Set[int] = set()

    async def initialize(self):
        """Pre-fetch and resolve destination entity IDs to prevent recursive feedback loops."""
        if self.config.primary_channel_id:
            self.ignored_chat_ids.add(self.config.primary_channel_id)
        if self.config.canva_channel_id:
            self.ignored_chat_ids.add(self.config.canva_channel_id)
        if self.config.vpn_channel_id:
            self.ignored_chat_ids.add(self.config.vpn_channel_id)
        if self.config.ai_channel_id:
            self.ignored_chat_ids.add(self.config.ai_channel_id)
        logger.info(f"Initialized HarvestEngine with {len(self.ignored_chat_ids)} protected destination targets.")

    async def handle_new_message(self, event):
        try:
            chat = await event.get_chat()
            chat_id = getattr(chat, 'id', None)
            chat_title = getattr(chat, 'title', getattr(chat, 'username', 'DirectMessage'))

            # Prevent recursive broadcasting to/from destination channels
            if chat_id in self.ignored_chat_ids:
                return

            raw_text = event.raw_text or ""
            if not raw_text.strip():
                return

            msg_uid = f"{chat_id}_{event.id}"
            if self.storage.is_processed(msg_uid):
                return

            findings = inspect_and_filter_message(raw_text, chat_title)
            if not findings:
                return

            msg_date = event.date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(event.date, 'strftime') else str(event.date)
            logger.info(f"🔥 [DROP DETECTED] [{chat_title}] Category: {findings[0]['category']}")

            # Save to local storage
            self.storage.save_alert(msg_uid, chat_title, msg_date, findings)

            # Desktop notification
            if self.config.enable_desktop_notifications:
                notify_desktop(f"🔥 رصد جديد: {findings[0]['category']}", f"[{chat_title}] {findings[0]['title']}")

            # Forward / Broadcast to Telegram Destinations
            await self._dispatch_findings(findings, chat_title, msg_date)

        except Exception as e:
            logger.error(f"Error handling incoming message: {e}", exc_info=True)

    async def _dispatch_findings(self, findings, chat_title: str, msg_date: str):
        for finding in findings:
            alert_text = format_telegram_alert(chat_title, msg_date, finding)
            cat = finding.get('category', '').lower()

            # 1. Primary Channel Broadcast
            if self.config.primary_channel_id:
                try:
                    await self._send_safe(self.config.primary_channel_id, alert_text)
                    logger.info(f"🚀 Sent to primary channel: {finding['category']}")
                except Exception as ex:
                    logger.error(f"Failed to broadcast to primary channel: {ex}")

            # 2. Category-Specific Routing
            # Canva Routing
            if 'canva' in cat and self.config.canva_channel_id:
                try:
                    await self._send_safe(
                        self.config.canva_channel_id,
                        alert_text,
                        reply_to=self.config.canva_topic_id
                    )
                    logger.info("🎨 Forwarded Canva drop to dedicated topic/channel")
                except Exception as ex:
                    logger.error(f"Failed to send to Canva channel: {ex}")

            # VPN Routing
            elif 'vpn' in cat and self.config.vpn_channel_id:
                try:
                    await self._send_safe(self.config.vpn_channel_id, alert_text)
                    logger.info("🛡️ Forwarded VPN drop to dedicated VPN channel")
                except Exception as ex:
                    logger.error(f"Failed to send to VPN channel: {ex}")

            # AI Routing
            elif any(k in cat for k in ['ai', 'gemini', 'chatgpt', 'claude']) and self.config.ai_channel_id:
                try:
                    await self._send_safe(self.config.ai_channel_id, alert_text)
                    logger.info("🤖 Forwarded AI drop to dedicated AI channel")
                except Exception as ex:
                    logger.error(f"Failed to send to AI channel: {ex}")

    async def _send_safe(self, target, text: str, reply_to: Optional[int] = None):
        kwargs = {'reply_to': reply_to} if reply_to else {}
        try:
            await self.client.send_message(target, text, parse_mode='md', **kwargs)
        except Exception:
            # Fallback to plain text if markdown formatting is rejected
            await self.client.send_message(target, text, parse_mode=None, **kwargs)
