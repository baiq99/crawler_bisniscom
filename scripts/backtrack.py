import sys
import os
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# import spider class (sesuaikan nama modul jika berbeda)
from bisnis_crawler.spiders.bisnis_spider import BisnisSpider

def ensure_dirs():
    os.makedirs("data/outputs", exist_ok=True)

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/backtrack.py <start_date> <end_date> [max_articles]")
        sys.exit(1)
    start = sys.argv[1]
    end = sys.argv[2]
    max_a = sys.argv[3] if len(sys.argv) > 3 else None

    ensure_dirs()
    outfile = f"data/outputs/bisnis_backtrack_{start}_{end}.jsonl"

    settings = get_project_settings()
    # override feed export to target file (jsonlines)
    settings.set("FEEDS", {
        outfile: {"format": "jsonlines", "encoding": "utf-8", "overwrite": True}
    })
    # optional: reduce log verbosity
    # settings.set("LOG_LEVEL", "INFO")

    process = CrawlerProcess(settings)
    spider_args = {"start_date": start, "end_date": end}
    if max_a:
        spider_args["max_articles"] = max_a

    # schedule the spider
    process.crawl(BisnisSpider, **spider_args)

    print("Starting spider (programmatic) ...")
    process.start()  # this will block until the crawl is finished
    print("Crawl finished. Output saved to:", outfile)

if __name__ == "__main__":
    main()
