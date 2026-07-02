from firecrawl import Firecrawl
from firecrawl.types import Source
from agents import function_tool

def get_search():
    f = Firecrawl(api_key="KEY HERE")

    @function_tool
    def search(query: str):
        for i in list(f.search(query)):
            print(i)
    return search