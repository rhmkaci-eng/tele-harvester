# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — Alert Formatting & Notification Dispatcher
Formats rich Telegram broadcast messages and triggers OS desktop notifications.
"""

import sys
import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger("TeleHarvester.Notifier")

def format_telegram_alert(source_name: str, msg_date_str: str, finding: Dict[str, Any]) -> str:
    """Renders a polished markdown alert message for Telegram."""
    lines = [
        f"🚨 **[رصد فوري - {finding['category']}]** ⚡",
        f"📡 **المصدر:** `{source_name}`",
        f"🕒 **التوقيت:** `{msg_date_str}`",
        "",
        f"📌 **{finding['title']}**",
    ]

    # Combos (Email:Password)
    combos = finding.get('combos', [])
    if combos:
        lines.append("")
        lines.append("🔑 **بيانات الحسابات (Combos):**")
        for c in combos[:5]:
            lines.append(f"• `{c['email']}:{c['password']}`")
        if len(combos) > 5:
            lines.append(f"• _...والمزيد ({len(combos)} حساب)_")

    # Links
    links = finding.get('links', [])
    if links:
        lines.append("")
        lines.append("🔗 **روابط التفعيل المباشرة:**")
        for l in links[:5]:
            lines.append(f"• {l}")

    # Codes
    codes = finding.get('codes', [])
    if codes and len(codes) <= 5:
        lines.append("")
        lines.append(f"🔢 **الأكواد / الرموز:** `{', '.join(codes)}`")

    return "\n".join(lines)

def notify_desktop(title: str, message: str):
    """Triggers a native Windows toast notification via PowerShell (non-blocking)."""
    if sys.platform != "win32":
        return

    try:
        clean_title = title.replace('"', '`"').replace("'", "’")
        clean_msg = message.replace('"', '`"').replace("'", "’").replace('\n', ' ')
        ps_cmd = f'''
        [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.BalloonTipTitle = "{clean_title}"
        $notify.BalloonTipText = "{clean_msg}"
        $notify.Visible = $True
        $notify.ShowBalloonTip(6000)
        '''
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        logger.debug(f"Desktop notification error: {e}")
