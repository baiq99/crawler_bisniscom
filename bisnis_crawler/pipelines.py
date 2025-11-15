import json
import scrapy
from datetime import datetime, timezone
from urllib.parse import urlparse

class NormalizeAndDedupPipeline:
    def __init__(self):
        self.seen = set()
        self.out_path = "data/outputs/bisnis_backtrack_2025-11-01_2025-11-15.jsonl.dedup.jsonl"
        self._fh = open(self.out_path, "w", encoding="utf-8")

    @classmethod
    def from_crawler(cls, crawler):
        # pipeline enabled via settings
        return cls()

    def _domain(self, link):
        try:
            return urlparse(link).netloc
        except Exception:
            return ""

    def process_item(self, item, spider):
        link = item.get("link") or ""
        if not link:
            # drop items without link
            raise scrapy.exceptions.DropItem("missing link")

        if link in self.seen:
            raise scrapy.exceptions.DropItem(f"duplicate link: {link}")
        self.seen.add(link)

        # ensure fields exist and normalized minimally
        item["title"] = (item.get("title") or "").strip()
        item["content"] = (item.get("content") or "").strip()
        item.setdefault("source", self._domain(link))
        item.setdefault("scraped_at", datetime.now(timezone.utc).isoformat())

        # write normalized JSONL
        self._fh.write(json.dumps(dict(item), ensure_ascii=False) + "\n")
        self._fh.flush()
        return item

    def close_spider(self, spider):
        try:
            self._fh.close()
        except Exception:
            pass
