"""
웹 크롤러 모듈
--------------------------------------------------
⚠️  크롤링 주의사항:
  - 반드시 robots.txt 및 이용약관 확인 후 사용
  - 과도한 요청으로 서버 부하 발생 금지 (rate limiting 적용)
  - 로그인 필요 페이지에 자격증명 사용 금지
--------------------------------------------------
skills/crawling_guide.skill.md 의 지침을 따른다.
"""
import re
import time
import logging
import urllib.request
import urllib.error
from typing import Optional
from datetime import datetime

from backend.core.models import CrawlResult
from backend.core.skill_loader import load_skill

logger = logging.getLogger(__name__)

# 크롤러 식별 User-Agent (투명한 봇 운영)
USER_AGENT = "CDPAIPlatform-Crawler/1.0 (ESG Research Bot; contact@company.internal)"
DEFAULT_DELAY = 2.0  # 요청 간 기본 대기시간 (초)


class WebCrawler:
    """
    정적 페이지 크롤러 (표준 라이브러리 기반).
    JS 렌더링이 필요한 경우 PlaywrightCrawler 사용.
    """

    def __init__(self, delay: float = DEFAULT_DELAY):
        self.delay = delay
        self._last_request_time: float = 0.0
        # SKILL.md에서 크롤링 가이드 로드
        try:
            self.guide = load_skill("crawling_guide")
        except FileNotFoundError:
            self.guide = ""
            logger.warning("crawling_guide.skill.md 없음")

    def _rate_limit(self):
        """요청 간 최소 대기시간 보장"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def _extract_text_from_html(self, html: str) -> str:
        """HTML에서 텍스트 추출 (BeautifulSoup 없이 기본 정제)"""
        # 스크립트/스타일 제거
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # 태그 제거
        text = re.sub(r"<[^>]+>", " ", html)
        # 연속 공백/줄바꿈 정리
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_title(self, html: str) -> Optional[str]:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    def _extract_links(self, html: str, base_url: str) -> list:
        """href 링크 추출 (동일 도메인만)"""
        links = re.findall(r'href=["\']([^"\'#]+)["\']', html, re.IGNORECASE)
        # 상대 URL 처리
        from urllib.parse import urljoin, urlparse
        base_domain = urlparse(base_url).netloc
        result = []
        for link in links:
            full = urljoin(base_url, link)
            if urlparse(full).netloc == base_domain:
                result.append(full)
        return list(set(result))[:20]  # 최대 20개

    def fetch(self, url: str) -> CrawlResult:
        """
        URL에서 컨텐츠를 가져온다.
        rate limiting 자동 적용.
        """
        self._rate_limit()
        logger.info(f"크롤링: {url}")

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # 인코딩 감지
                content_type = resp.headers.get("Content-Type", "")
                encoding = "utf-8"
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].split(";")[0].strip()

                html = raw.decode(encoding, errors="replace")
                text = self._extract_text_from_html(html)
                title = self._extract_title(html)
                links = self._extract_links(html, url)

                return CrawlResult(
                    url=url,
                    title=title,
                    content=text[:50000],  # 최대 50KB 텍스트
                    links=links,
                    crawled_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    success=True,
                )

        except urllib.error.HTTPError as e:
            return CrawlResult(url=url, content="", success=False, error=f"HTTP {e.code}")
        except Exception as e:
            return CrawlResult(url=url, content="", success=False, error=str(e))

    def fetch_multiple(self, urls: list) -> list:
        """여러 URL 순차 크롤링 (rate limiting 자동 적용)"""
        return [self.fetch(url) for url in urls]


class PlaywrightCrawler:
    """
    JS 렌더링이 필요한 동적 페이지용 크롤러.
    사용 전 : playwright install chromium
    Docker 환경에서는 자동 설치됨.
    """

    def __init__(self, headless: bool = True, delay: float = DEFAULT_DELAY):
        self.headless = headless
        self.delay = delay

    def fetch(self, url: str, wait_for: Optional[str] = None) -> CrawlResult:
        """
        Playwright로 JS 렌더링 후 컨텐츠 수집.
        wait_for: CSS 셀렉터 (해당 요소가 나타날 때까지 대기)
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return CrawlResult(
                url=url,
                content="",
                success=False,
                error="Playwright 미설치: pip install playwright && playwright install chromium",
            )

        time.sleep(self.delay)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page(
                    user_agent=USER_AGENT,
                    extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9"},
                )
                page.goto(url, timeout=30000)
                if wait_for:
                    page.wait_for_selector(wait_for, timeout=10000)
                else:
                    page.wait_for_load_state("networkidle", timeout=15000)

                title = page.title()
                content = page.inner_text("body") or ""
                links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.href).filter(h => h.startsWith('http')).slice(0, 20)",
                )
                browser.close()

                return CrawlResult(
                    url=url,
                    title=title,
                    content=content[:50000],
                    links=links,
                    crawled_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    success=True,
                )
        except Exception as e:
            return CrawlResult(url=url, content="", success=False, error=str(e))


def get_crawler(use_playwright: bool = False) -> WebCrawler:
    """크롤러 팩토리"""
    if use_playwright:
        return PlaywrightCrawler()
    return WebCrawler()
