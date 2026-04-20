import urllib.parse
import urllib.request
import json
import re


def _fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ClaudeAgent/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo HTML 검색 결과 파싱."""
    try:
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        html = _fetch(url)

        results = []
        link_pat = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>')
        snip_pat = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)

        links = link_pat.findall(html)
        snippets = snip_pat.findall(html)

        for i, (href, title) in enumerate(links[:max_results]):
            snip = re.sub(r'<[^>]+>', '', snippets[i]) if i < len(snippets) else ""
            snip = re.sub(r'\s+', ' ', snip).strip()
            title = re.sub(r'\s+', ' ', title).strip()
            if href.startswith("//duckduckgo.com/l/?uddg="):
                m = re.search(r'uddg=([^&]+)', href)
                if m:
                    href = urllib.parse.unquote(m.group(1))
            results.append(f"{i+1}. {title}\n   {href}\n   {snip[:180]}")

        return "\n\n".join(results) if results else "검색 결과 없음"
    except Exception as e:
        return f"웹 검색 실패: {e}"


def fetch_url(url: str, max_chars: int = 4000) -> str:
    """URL 내용 가져오기 (HTML 태그 제거)."""
    try:
        html = _fetch(url)
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"URL 가져오기 실패: {e}"
