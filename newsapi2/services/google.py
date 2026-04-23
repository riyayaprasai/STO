import aiohttp
from bs4 import BeautifulSoup

async def get_google_news(query: str):
    """Get news from Google News."""
    search_url = f"https://news.google.com/search?q={query}+when:7d&hl=en-US&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, headers=headers) as res:
                content = await res.text()
                
        soup = BeautifulSoup(content, "html.parser")

        articles = []
        for item in soup.select("article")[:10]:
            headline_tag = item.select_one("h3 a, h4 a")
            if headline_tag:
                title = headline_tag.text
                link = "https://news.google.com" + headline_tag['href'][1:]
                articles.append({
                    "title": title,
                    "link": link,
                    "source": "Google"
                })

        return articles
    except Exception as e:
        print(f"Error fetching Google News: {e}")
        return [] 