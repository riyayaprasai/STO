import logging
import httpx
import trafilatura
from PyPDF2 import PdfReader
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid thrashing external sites during development/testing
_cache = {}

async def extract_text(url: str) -> Optional[str]:
    """
    Detects if a URL is a PDF or HTML, fetches it, and extracts the core text content.
    """
    if not url:
        return None
    
    if url in _cache:
        return _cache[url]

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            if "sec.gov" in url.lower() or "edgar" in url.lower():
                headers["User-Agent"] = "Research Tool research@example.com"
                
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            
            # 1. Handle PDF
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                text = extract_from_pdf(response.content)
            # 2. Handle HTML
            else:
                text = extract_from_html(response.text)

            if text:
                # Clean up whitespace and limit length to avoid token bloat
                text = " ".join(text.split())
                _cache[url] = text
                return text
            
            return None

    except Exception as e:
        logger.warning(f"Failed to extract content from {url}: {e}")
        return None

def extract_from_html(html_content: str) -> Optional[str]:
    """Uses trafilatura to get clean body text from HTML."""
    return trafilatura.extract(html_content, include_comments=False, include_tables=True)

def extract_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """Uses PyPDF2 to extract text from a PDF binary."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        # Only take the first 15 pages max for uploads
        for page in reader.pages[:15]:
            text += page.extract_text() + "\n"
        return text if text.strip() else None
    except Exception as e:
        logger.warning(f"PDF extraction error: {e}")
        return None

if __name__ == "__main__":
    # Quick standalone test
    import asyncio
    
    async def test():
        # Test HTML
        print("Testing HTML extraction...")
        html_text = await extract_text("https://en.wikipedia.org/wiki/Apple_Inc.")
        print(f"HTML Length: {len(html_text) if html_text else 0}")
        if html_text: print(f"Preview: {html_text[:200]}...")

        # Test PDF (Apple 10-K sample or similar)
        # Note: This might fail if the URL is blocked or down, but provides a pattern.
        print("\nTesting PDF extraction...")
        # Using a reliable public PDF for test
        pdf_text = await extract_text("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf")
        print(f"PDF Length: {len(pdf_text) if pdf_text else 0}")
        if pdf_text: print(f"Preview: {pdf_text[:200]}...")

    asyncio.run(test())
