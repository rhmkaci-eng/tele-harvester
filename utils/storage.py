# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — Alert Persistence & Duplicate Prevention
Safely archives extracted drops to JSON and Markdown.
"""

import json
import logging
from pathlib import Path
from typing import Set, Dict, List, Any

logger = logging.getLogger("TeleHarvester.Storage")

class AlertStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.json_file = data_dir / "alerts.json"
        self.md_file = data_dir / "alerts.md"
        self.processed_ids: Set[str] = self._load_processed_ids()

    def _load_processed_ids(self) -> Set[str]:
        ids = set()
        if self.json_file.exists():
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        if "uid" in item:
                            ids.add(str(item["uid"]))
            except Exception as e:
                logger.warning(f"Could not load existing alert cache: {e}")
        return ids

    def is_processed(self, msg_uid: str) -> bool:
        return str(msg_uid) in self.processed_ids

    def save_alert(self, msg_uid: str, source_title: str, msg_date: str, findings: List[Dict[str, Any]]):
        if self.is_processed(msg_uid):
            return

        self.processed_ids.add(str(msg_uid))

        # Save to JSON
        try:
            records = []
            if self.json_file.exists():
                with open(self.json_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
            records.append({
                "uid": str(msg_uid),
                "source": source_title,
                "date": msg_date,
                "findings": findings
            })
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error persisting to JSON: {e}")

        # Save to Markdown
        try:
            with open(self.md_file, "a", encoding="utf-8") as f:
                for fd in findings:
                    f.write(f"\n### 🚨 [Alert - {fd['category']}] ({msg_date})\n")
                    f.write(f"**Source:** `{source_title}`\n\n")
                    f.write(f"**{fd['title']}**\n\n")
                    if fd.get("combos"):
                        f.write("- 🔑 **Credentials:**\n")
                        for c in fd["combos"]:
                            f.write(f"  - `{c['email']}:{c['password']}`\n")
                    if fd.get("links"):
                        f.write("- 🔗 **Direct Links:**\n")
                        for l in fd["links"]:
                            f.write(f"  - [{l}]({l})\n")
                    if fd.get("codes"):
                        f.write(f"- 🔢 **Codes / Keys:** `{', '.join(fd['codes'])}`\n")
                    f.write(f"\n> **Raw Snippet:**\n```text\n{fd['raw'].strip()[:500]}\n```\n")
                    f.write("---\n")
        except Exception as e:
            logger.error(f"Error persisting to Markdown: {e}")
