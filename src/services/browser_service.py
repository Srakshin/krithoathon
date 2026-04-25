"""Browser-backed page rendering for sources that require JavaScript."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from ..domain.models import WebSourceConfig

logger = logging.getLogger(__name__)


@dataclass
class RenderedPage:
    requested_url: str
    final_url: str
    title: str
    html: str
    text: str
    status_code: int | None = None


class BrowserService:
    """Render pages with Playwright while keeping secrets in the environment."""

    async def fetch(self, source: WebSourceConfig) -> RenderedPage:
        attempts = max(1, int(source.retry_attempts))
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return await self._fetch_once(source)
            except Exception as exc:  # pragma: no cover - runtime/browser-dependent
                last_error = exc
                logger.warning(
                    "Browser fetch failed for %s (attempt %s/%s): %s",
                    source.name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt == attempts:
                    break
                await asyncio.sleep(min(1.5 * attempt, 5.0))

        if last_error is None:  # pragma: no cover - defensive
            raise RuntimeError(f"Browser fetch failed for {source.name}")
        raise last_error

    async def _fetch_once(self, source: WebSourceConfig) -> RenderedPage:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise RuntimeError(
                "Playwright is required for browser scraping. Install dependencies "
                "and run `python -m playwright install chromium`."
            ) from exc

        timeout_ms = max(1, int(float(source.timeout_seconds) * 1000))
        browser = None
        context = None

        async with async_playwright() as playwright:
            try:
                launch_options: dict[str, Any] = {"headless": True}
                proxy_url = self._read_env(source.browser.auth.proxy_env)
                if proxy_url:
                    launch_options["proxy"] = {"server": proxy_url}

                browser = await playwright.chromium.launch(**launch_options)

                context_options: dict[str, Any] = {}
                storage_state_path = self._read_env(source.browser.auth.storage_state_env)
                if storage_state_path:
                    context_options["storage_state"] = storage_state_path

                user_agent = self._read_env(source.browser.auth.user_agent_env)
                if user_agent:
                    context_options["user_agent"] = user_agent

                context = await browser.new_context(**context_options)

                extra_headers = self._read_json_object_env(source.browser.auth.headers_env)
                if extra_headers:
                    await context.set_extra_http_headers(extra_headers)

                cookies = self._read_json_list_env(source.browser.auth.cookies_env)
                if cookies:
                    await context.add_cookies(cookies)

                page = await context.new_page()
                page.set_default_timeout(timeout_ms)
                page.set_default_navigation_timeout(timeout_ms)

                session_storage = self._read_json_object_env(source.browser.auth.session_storage_env)
                if session_storage:
                    await page.add_init_script(
                        """
                        (entries) => {
                          for (const [key, value] of Object.entries(entries)) {
                            window.sessionStorage.setItem(key, value);
                          }
                        }
                        """,
                        session_storage,
                    )

                response = await page.goto(
                    str(source.url),
                    wait_until=source.browser.wait_until,
                    timeout=timeout_ms,
                )

                if source.browser.wait_for_selector:
                    await page.wait_for_selector(source.browser.wait_for_selector, timeout=timeout_ms)

                for _ in range(max(0, int(source.browser.scroll_steps))):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(max(0, int(source.browser.scroll_pause_ms)))

                html = await page.content()
                title = await page.title()
                text = ""
                try:
                    text = await page.locator("body").inner_text(timeout=min(timeout_ms, 5000))
                except Exception:  # pragma: no cover - best effort extraction
                    text = ""

                return RenderedPage(
                    requested_url=str(source.url),
                    final_url=page.url,
                    title=title or source.name,
                    html=html,
                    text=text,
                    status_code=response.status if response else None,
                )
            finally:  # pragma: no branch - cleanup only
                if context is not None:
                    await context.close()
                if browser is not None:
                    await browser.close()

    @staticmethod
    def _read_env(name: str | None) -> str | None:
        if not name:
            return None
        value = os.getenv(name, "").strip()
        if value:
            return value
        raise RuntimeError(f"Missing required environment variable: {name}")

    def _read_json_object_env(self, name: str | None) -> dict[str, str] | None:
        if not name:
            return None
        raw = self._read_env(name)
        if not raw:
            return None
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Environment variable {name} must contain a JSON object.")
        return {str(key): str(value) for key, value in payload.items()}

    def _read_json_list_env(self, name: str | None) -> list[dict[str, Any]] | None:
        if not name:
            return None
        raw = self._read_env(name)
        if not raw:
            return None
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise RuntimeError(f"Environment variable {name} must contain a JSON array.")
        return payload
