from firecrawl import Firecrawl
from firecrawl.types import Source
from agents import function_tool

def get_search():
    f = Firecrawl(api_key="KEY HERE")

    @function_tool
    def search(query: str, count: int):
        for i in list(f.search(query, limit=count)):
            print(i)

    @function_tool
    def read_page(url: str):
        return f.scrape(url).markdown
    return search, read_page