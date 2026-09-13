"""Conservative public web fallback. Results are references, never auto-published steps."""

import re
from urllib.parse import quote, unquote

import httpx

from backend.models import WebResult


class WebSearcher:
    def search(self, query: str, limit: int = 3) -> list[WebResult]:
        url = "https://html.duckduckgo.com/html/?q=" + quote(query + " iPhone LINE 教學")
        try:
            response = httpx.get(url, timeout=8, headers={"User-Agent": "elder-guide/0.1"})
            response.raise_for_status()
            html = response.text
        except httpx.HTTPError:
            return []
        results = []
        for match in re.finditer(
            r'class="result__a" href="(.*?)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
            html,
            re.S,
        ):
            href, title, snippet = match.groups()
            href = unquote(re.sub(r".*uddg=", "", href))
            if not href.startswith(("http://", "https://")):
                continue

            def clean(value: str) -> str:
                return re.sub(r"<[^>]+>", "", value).strip()

            try:
                results.append(
                    WebResult(title=clean(title)[:200], url=href, snippet=clean(snippet)[:500])
                )
            except ValueError:
                continue
            if len(results) >= limit:
                break
        return results
