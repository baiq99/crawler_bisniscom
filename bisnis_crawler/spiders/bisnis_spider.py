import scrapy
from datetime import datetime, time
from ..items import ArticleItem
from .helpers import parse_date_to_iso, clean_paragraphs, clean_text
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BisnisSpider(scrapy.Spider):
    name = "bisnis"
    allowed_domains = [
        "bisnis.com",
        "finansial.bisnis.com",
        "sumatra.bisnis.com",
        "market.bisnis.com",
        "kabar24.bisnis.com",
        "teknologi.bisnis.com",
        "plus.bisnis.com",
        "premium.bisnis.com",
        "video.bisnis.com",
        "interaktif.bisnis.com",
        "hijau.bisnis.com",
        "bandung.bisnis.com",
        "semarang.bisnis.com",
        "surabaya.bisnis.com",
        "koran.bisnis.com",
        "infografik.bisnis.com",
    ]
    start_urls = ["https://www.bisnis.com/"]

    custom_settings = {
        # per-spider override jika perlu
    }

    def __init__(self, start_date=None, end_date=None, max_articles=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # parse start_date (ke Asia/Jakarta)
        try:
            self.start_date = (
                parse_date_to_iso(start_date, tz="Asia/Jakarta", assume_utc_if_naive=True)
                if start_date
                else None
            )
        except Exception:
            logger.warning("Gagal parse start_date=%r, mengabaikan filter start_date.", start_date)
            self.start_date = None

        # parse end_date -> treat as end of day (23:59:59) in Asia/Jakarta
        try:
            if end_date:
                # normalize end_date to end of day
                # appending time ensures inclusive range
                end_iso = parse_date_to_iso(f"{end_date} 23:59:59", tz="Asia/Jakarta", assume_utc_if_naive=True)
                self.end_date = end_iso
            else:
                self.end_date = None
        except Exception:
            logger.warning("Gagal parse end_date=%r, mengabaikan filter end_date.", end_date)
            self.end_date = None

        self.max_articles = int(max_articles) if max_articles else None
        self.collected = 0

        # prepare datetime objects for comparisons (aware datetimes expected)
        try:
            self._start_dt = datetime.fromisoformat(self.start_date) if self.start_date else None
        except Exception:
            self._start_dt = None
        try:
            self._end_dt = datetime.fromisoformat(self.end_date) if self.end_date else None
        except Exception:
            self._end_dt = None

    def parse(self, response):
        # collect article links (heuristic)
        links = response.css("a[href*='/read/']::attr(href)").getall()
        # also try article listing blocks
        links += response.css("article a::attr(href)").getall()
        for href in links:
            if not href:
                continue
            url = response.urljoin(href)
            # basic domain check to avoid leaving site
            p = urlparse(url)
            if "bisnis.com" not in p.netloc:
                continue
            yield response.follow(url, callback=self.parse_article)

        # pagination (several patterns)
        next_page = (
            response.css("a.next::attr(href)").get()
            or response.css(".pagination a[rel='next']::attr(href)").get()
            or response.css(".paging a.next::attr(href)").get()
        )
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def _is_non_text_url(self, url: str) -> bool:
        # skip known non-article paths or subdomains
        parsed = urlparse(url)
        if parsed.netloc.startswith("video.") or parsed.netloc.startswith("infografik."):
            return True
        # skip if path includes segments that identify non-text content
        bad_segments = ["/video/", "/infografik/", "/interaktif/", "/premium/"]
        if any(seg in parsed.path for seg in bad_segments):
            return True
        return False

    def parse_article(self, response):
        link = response.url

        if self._is_non_text_url(link):
            logger.debug("Skip non-text URL: %s", link)
            return

        # title
        title = (
            response.css("h1::text").get()
            or response.css("meta[property='og:title']::attr(content)").get()
            or response.css("meta[name='twitter:title']::attr(content)").get()
            or ""
        )

        # paragraphs: try to get paragraph nodes, but also fallback to container string()
        paragraphs = response.css("article p, div.article-content p, div.detail_text p, div[itemprop='articleBody'] p, .article-body p").xpath("string(.)").getall()
        # clean and join
        content = clean_paragraphs(paragraphs, min_total_length=40)

        # fallback: container text if paragraphs empty
        if not content:
            container_text = (
                response.css("div.article-content, div.detail_text, article, .article-body")
                .xpath("string(.)")
                .get()
            )
            content = clean_text(container_text)

        # extract date from common places
        date_sel = (
            response.css("meta[property='article:published_time']::attr(content)").get()
            or response.css("meta[name='pubdate']::attr(content)").get()
            or response.css("time::attr(datetime)").get()
            or response.xpath("//*[contains(@class,'date') or contains(@class,'time')]/text()").get()
        )

        published_at = None
        if date_sel:
            try:
                published_at = parse_date_to_iso(date_sel, tz="Asia/Jakarta", assume_utc_if_naive=True)
            except Exception as e:
                logger.debug("Gagal parse tanggal %r pada %s: %s", date_sel, link, e)
                published_at = None

        # if date filter active and no published_at -> skip
        if (self._start_dt or self._end_dt) and not published_at:
            logger.debug("Skip %s karena tidak punya published_at saat filter tanggal aktif.", link)
            return

        # compare dates (both sides should be aware datetimes)
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at)
                if self._start_dt and pub_dt < self._start_dt:
                    logger.debug("Skip %s karena pub_dt < start_date", link)
                    return
                if self._end_dt and pub_dt > self._end_dt:
                    logger.debug("Skip %s karena pub_dt > end_date", link)
                    return
            except Exception as e:
                logger.debug("Error saat membandingkan tanggal untuk %s: %s", link, e)
                return

        # if content still short, skip
        if not content or len(content) < 40:
            logger.debug("Skip %s karena content too short (%s).", link, len(content) if content else 0)
            return

        item = ArticleItem(
            link=link,
            title=clean_text(title),
            content=clean_text(content),
            published_at=published_at,
        )

        yield item

        self.collected += 1
        if self.max_articles and self.collected >= self.max_articles:
            logger.info("Reached max_articles (%s), stopping.", self.max_articles)
            raise scrapy.exceptions.CloseSpider("max_articles_reached")
