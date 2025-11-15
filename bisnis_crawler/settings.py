BOT_NAME = "bisnis_crawler"
SPIDER_MODULES = ["bisnis_crawler.spiders"]
NEWSPIDER_MODULE = "bisnis_crawler.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 1.0            
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0

# pipelines 
ITEM_PIPELINES = {
    "business_crawler.pipelines.NormalizeAndDedupPipeline": 300,
}

LOG_LEVEL = "INFO"
