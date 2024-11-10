import asyncio
from html.parser import HTMLParser

from httpx import AsyncClient

OIL_PRICE_URL = "https://homefuelsdirect.co.uk/home/heating-oil-prices/cambridgeshire"


class SpanExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.spans = []
        self.in_span = False

    def handle_starttag(self, tag, attrs):
        if tag == "span":
            self.in_span = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.in_span = False

    def handle_data(self, data):
        if self.in_span:
            self.spans.append(data)


def extract_spans(html_content):
    parser = SpanExtractor()
    parser.feed(html_content)
    return parser.spans


async def fetch_and_extract_spans(url) -> list[str]:
    async with AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return extract_spans(response.text)


async def main():
    spans = await fetch_and_extract_spans(OIL_PRICE_URL)
    for i, span in enumerate(spans):
        if "Current Price" in span:
            print(spans[i + 1])


asyncio.run(main())
