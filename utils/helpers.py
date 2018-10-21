"""Defines helper functions used across classes."""
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    """Builds an HTML parser."""
    def handle_data(self, data):
        if data.startswith("\nvar data;"):
            list_start = data.find("[")
            list_end = data.find("]")
            clan_members = data[list_start+1:list_end]
            clan_members = clan_members.split(", ")
            clan_list = []
            for item in clan_members:
                add_item = item[1:-1]
                add_item = add_item.replace(u'\xa0', u' ')
                clan_list.append(add_item)
            self.data = clan_list

async def fetch(session, url):
    """Fetches a web request asynchronously."""
    async with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()

async def get_clan_list():
    """Gets the list of clan members."""
    clan_parser = MyHTMLParser()
    async with aiohttp.ClientSession() as session:
        req_html = await fetch(session, clan_url)
    clan_parser.feed(req_html)
    clan_list = clan_parser.data
    return clan_list
