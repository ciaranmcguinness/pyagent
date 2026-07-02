from firecrawl import Firecrawl
from firecrawl.types import Source
from agents import function_tool

def get_search(key):
    f = Firecrawl(api_key=key)

    @function_tool
    def search(query: str, count: int):
        return list(filter(lambda x: x[1] != None, f.search(query, limit=count)))
    @function_tool
    def read_page(url: str):
        return f.scrape(url).markdown
    return search, read_page