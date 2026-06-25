import httpx
from bs4 import BeautifulSoup

async def scrape_company_url(url: str) -> str:
    """
    Fetches the content of a URL and extracts all paragraph text using BeautifulSoup.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return ""
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # We add a User-Agent to avoid getting immediately blocked by basic bot protection
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text from paragraphs, headers, and list items
            texts = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
            content = " ".join([t.get_text(strip=True) for t in texts if t.get_text(strip=True)])
            
            # Limit the content length to avoid massive token consumption (first 20,000 characters ~ 5000 tokens)
            return content[:20000]
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return ""
