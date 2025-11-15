import scrapy

class ArticleItem(scrapy.Item):
    link = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    published_at = scrapy.Field()  # ISO 8601 string
