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

    def save_summary(self, summary_md: str, date: str, language: str = "en") -> None:
        """Save summary to data_dir/summaries and potentially docs/_posts."""
        filename = f"{date}-summary-{language}.md"
        
        # Save to local data/summaries/
        local_path = self.summaries_dir / filename
        local_path.write_text(summary_md, encoding="utf-8")
        
        # Attempt to publish to docs/_posts if it exists
        # Navigate up to the project root assuming data/ is inside it or next to it
        # Actually self.data_dir is usually at project root.
        docs_posts_dir = self.data_dir.parent / "docs" / "_posts"
        if docs_posts_dir.exists() and docs_posts_dir.is_dir():
            post_filename = f"{date}-morning-pulse-{language}.md"
            docs_path = docs_posts_dir / post_filename
            # Prepend Jekyll/Hugo frontmatter if we wanted, but the prompt just says save a copy
            docs_path.write_text(summary_md, encoding="utf-8")
