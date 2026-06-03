import scrapy


class DiscoveredUrlItem(scrapy.Item):
    source_key = scrapy.Field()
    url = scrapy.Field()
    discovered_from = scrapy.Field()
    depth = scrapy.Field()
