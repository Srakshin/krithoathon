"""File-backed storage for configuration, summaries, and subscribers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..domain.models import Config


class FileStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.config_path = self.data_dir / "config.json"
        self.summaries_dir = self.data_dir / "summaries"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Config:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Please create it based on data/config.example.json"
            )

        return Config.model_validate(json.loads(self.config_path.read_text(encoding="utf-8")))

    def save_config(self, config: Config, backup: bool = True) -> Path:
        if backup and self.config_path.exists():
            shutil.copy2(self.config_path, self.config_path.with_suffix(".json.bak"))

        self.config_path.write_text(
            json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return self.config_path


    def load_subscribers(self) -> list[str]:
        subscribers_path = self.data_dir / "subscribers.json"
        if not subscribers_path.exists():
            return []

        try:
            return json.loads(subscribers_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def add_subscriber(self, email_address: str) -> None:
        subscribers = self.load_subscribers()
        if email_address not in subscribers:
            subscribers.append(email_address)
            self._save_subscribers(subscribers)

    def remove_subscriber(self, email_address: str) -> None:
        subscribers = self.load_subscribers()
        if email_address in subscribers:
            subscribers.remove(email_address)
            self._save_subscribers(subscribers)

    def _save_subscribers(self, subscribers: list[str]) -> None:
        subscribers_path = self.data_dir / "subscribers.json"
        subscribers_path.write_text(json.dumps(subscribers, indent=2), encoding="utf-8")
