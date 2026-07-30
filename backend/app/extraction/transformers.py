from __future__ import annotations

import csv
import io
import json
from typing import Any, Optional


class DataTransformer:
    @staticmethod
    def to_json(data: Any, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(data, indent=2, default=str, ensure_ascii=False)
        return json.dumps(data, default=str, ensure_ascii=False)

    @staticmethod
    def to_csv(data: list[dict], fields: Optional[list[str]] = None) -> str:
        if not data:
            return ""

        fieldnames = fields or list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def flatten_json(data: dict, parent_key: str = "", sep: str = "_") -> dict:
        items: dict[str, Any] = {}
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(DataTransformer.flatten_json(v, new_key, sep=sep))
            elif isinstance(v, list):
                items[new_key] = json.dumps(v, default=str)
            else:
                items[new_key] = v
        return items

    @staticmethod
    def clean_html_content(html: str) -> str:
        import re

        # Remove scripts and styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove empty lines
        text = re.sub(r"\n\s*\n", "\n", text)
        return text.strip()

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        import re

        url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[-\w./?%&=+#]*"
        return list(set(re.findall(url_pattern, text)))

    @staticmethod
    def extract_emails(text: str) -> list[str]:
        import re

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return list(set(re.findall(email_pattern, text)))

    @staticmethod
    def truncate_text(text: str, max_chars: int = 100000) -> str:
        if len(text) <= max_chars:
            return text
        return (
            text[:max_chars]
            + f"\n\n[... truncated, {len(text) - max_chars} chars removed]"
        )
