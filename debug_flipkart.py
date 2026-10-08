import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re, json
from urllib.parse import urlparse, quote

# Test both a product that worked before and Samsung
test_urls = [
    'https://www.flipkart.com/apple-iphone-15/p/itmbf14ef54f645d',
    'https://www.flipkart.com/samsung-galaxy-m15-5g/p/itmdb4b0e8224592',
]

base_headers = {
    'Accept-Language': 'en-IN,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/',
    'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'cross-site',
    'upgrade-insecure-requests': '1',
}

for url in test_urls:
    print(f"\n{'='*60}")
    print(f"URL: {url[:70]}")
    
    # Try 1: Direct fetch (no session, no homepage warmup)
    try:
        r = cffi_requests.get(url, impersonate='chrome120', timeout=20, headers=base_headers)
        html = r.content.decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')
        title_text = title.get_text()[:80] if title else 'None'
        has_rupee = '\u20b9' in html
        print(f"Direct fetch: status={r.status_code}, title={title_text}")
        print(f"  Has rupee: {has_rupee}, HTML size: {len(html)}")
        
        if has_rupee:
            # Find what class the price element has
            for tag in soup.find_all(['span', 'div']):
                text = tag.get_text(strip=True)
                if text.startswith('\u20b9') and len(text) < 20:
                    print(f"  Price element: class={tag.get('class')} text={text}")
                    break
    except Exception as e:
        print(f"Direct fetch error: {e}")
    
    # Try 2: Fetch with m.flipkart.com (mobile site)
    try:
        mobile_url = url.replace('www.flipkart.com', 'm.flipkart.com')
        r2 = cffi_requests.get(mobile_url, impersonate='chrome120', timeout=20, headers={
            'Accept-Language': 'en-IN,en;q=0.9',
            'Referer': 'https://www.google.com/',
        })
        html2 = r2.content.decode('utf-8', errors='replace')
        soup2 = BeautifulSoup(html2, 'html.parser')
        title2 = soup2.find('title')
        title_text2 = title2.get_text()[:80] if title2 else 'None'
        has_rupee2 = '\u20b9' in html2
        print(f"Mobile fetch: status={r2.status_code}, title={title_text2}")
        print(f"  Has rupee: {has_rupee2}, HTML size: {len(html2)}")
        
        if has_rupee2:
            for tag in soup2.find_all(['span', 'div']):
                text = tag.get_text(strip=True)
                if text.startswith('\u20b9') and len(text) < 20:
                    print(f"  Price element: class={tag.get('class')} text={text}")
                    break
    except Exception as e:
        print(f"Mobile fetch error: {e}")

    # Try 3: Flipkart product API
    try:
        parsed = urlparse(url)
        # Extract PID from URL path
        pid_match = re.search(r'/p/(itm[a-z0-9]+)', parsed.path)
        if pid_match:
            pid = pid_match.group(1)
            api_url = f'https://www.flipkart.com/api/3/page/fetch?url={quote(parsed.path)}'
            r3 = cffi_requests.get(api_url, impersonate='chrome120', timeout=20, headers={
                'Accept': 'application/json',
                'Accept-Language': 'en-IN,en;q=0.9',
                'Origin': 'https://www.flipkart.com',
                'Referer': url,
                'x-user-agent': 'Mozilla/5.0 FKUA/website/42/website/Desktop',
            })
            print(f"API fetch (www): status={r3.status_code}")
            if r3.status_code == 200:
                print(f"  Response: {r3.text[:300]}")
    except Exception as e:
        print(f"API fetch error: {e}")
