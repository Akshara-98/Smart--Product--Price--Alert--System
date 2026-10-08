import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import requests
try:
    from curl_cffi import requests as cffi_requests
    CURL_CFFI_AVAILABLE = True
except Exception:
    CURL_CFFI_AVAILABLE = False

from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import json

# Standard headers for plain requests fallback
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Supported domains
SUPPORTED_DOMAINS = [
    'amazon.in', 'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.ca', 'amazon.co.jp',
    'amzn.to', 'amzn.eu',
    'flipkart.com', 'shopsy.in',
    'myntra.com',
    'meesho.com',
    'ajio.com',
    'nykaa.com',
    'snapdeal.com',
    'tatacliq.com',
    'reliancedigital.in',
    'croma.com',
]

def is_supported_url(url):
    """Check if a URL is a valid web URL."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
    except Exception:
        return False
    except Exception:
        return False

def extract_numeric(text):
    """Extract a numeric price value from a string."""
    if not text:
        return None
    # Remove currency symbols, commas, non-breaking spaces
    cleaned = re.sub(r'[^\d.]', '', str(text).replace(',', '').replace('\xa0', ''))
    try:
        if cleaned.count('.') > 1:
            # Handle European formats like 1.234,56 where dots are separators
            parts = cleaned.split('.')
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None

def safe_fetch(url, use_cffi=False, impersonate='chrome120', timeout=20):
    """
    Fetch a URL and return (response_bytes, response_text, status_code).
    """
    if use_cffi and CURL_CFFI_AVAILABLE:
        r = cffi_requests.get(
            url,
            impersonate=impersonate,
            timeout=timeout,
            headers={"Accept-Language": "en-IN,en;q=0.9,en-US;q=0.8"}
        )
        r.raise_for_status()
        content = r.content
        text = r.content.decode('utf-8', errors='replace')
        return content, text, r.status_code
    else:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        content = r.content
        text = content.decode('utf-8', errors='replace')
        return content, text, r.status_code

# ──────────────────────────────────────────────
#  Amazon Scraper & Fetcher
# ──────────────────────────────────────────────

def _fetch_amazon_with_session(url):
    """
    Fetch Amazon using curl_cffi with Safari/mobile impersonation first (very reliable against bot blockers).
    """
    if not CURL_CFFI_AVAILABLE:
        return safe_fetch(url, use_cffi=False)

    session = cffi_requests.Session()
    headers_mobile = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
    }
    
    try:
        r = session.get(url, impersonate='safari15_5', timeout=20, headers=headers_mobile)
        if r.status_code == 200 and "validateCaptcha" not in r.text:
            content = r.content
            html_text = content.decode('utf-8', errors='replace')
            return content, html_text, r.status_code
    except Exception:
        pass

    # Fallback to desktop Chrome impersonation
    headers_desktop = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9,en-US;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    domain = urlparse(url).netloc
    try:
        session.get(f"https://{domain}/", impersonate='chrome120', timeout=10, headers=headers_desktop)
    except Exception:
        pass

    r = session.get(url, impersonate='chrome120', timeout=25, headers=headers_desktop)
    r.raise_for_status()
    content = r.content
    html_text = content.decode('utf-8', errors='replace')
    return content, html_text, r.status_code

def scrape_amazon(soup, html_text):
    name = "Unknown Amazon Product"
    title_elem = soup.find(id="productTitle") or soup.find(id="title")
    if title_elem:
        name = title_elem.get_text(strip=True)
    else:
        t = soup.find('title')
        if t:
            name = t.get_text().split(' :')[0].split(' - Amazon')[0].split(': Amazon')[0].strip()

    price = None

    # Priority 1: High accuracy price selectors
    selectors = [
        'span.priceToPay span.a-offscreen',
        '.reinventPricePriceToPayMargin span.a-offscreen',
        '#corePriceDisplay_desktop_feature_div .a-price-whole',
        '#corePriceDisplay_desktop_feature_div span.a-offscreen',
        '#corePrice_desktop_feature_div .a-price-whole',
        '#corePrice_desktop_feature_div span.a-offscreen',
        '.apexPriceToPay span.a-offscreen',
        '#priceblock_ourprice',
        '#priceblock_dealprice',
        '#priceblock_saleprice',
        '#price_inside_buybox',
        '.a-price.a-text-price.a-size-medium .a-offscreen',
        '#corePrice_desktop .a-price .a-offscreen',
        '.a-price .a-offscreen',
        '.a-price-whole',
        '.a-color-price',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            val = extract_numeric(el.get_text())
            if val and val > 0:
                price = val
                break

    # Priority 2: JSON-LD structured data
    if not price:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                if isinstance(data, dict):
                    offers = data.get('offers', {})
                    if isinstance(offers, dict) and offers.get('price'):
                        price = float(offers['price'])
                        break
                    elif isinstance(offers, list):
                        for offer in offers:
                            if offer.get('price'):
                                price = float(offer['price'])
                                break
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'offers' in item:
                            offers = item.get('offers', {})
                            if isinstance(offers, dict) and offers.get('price'):
                                price = float(offers['price'])
                                break
                if price:
                    break
            except Exception:
                pass

    # Priority 3: Meta tags
    if not price:
        for meta_name in [('itemprop', 'price'), ('property', 'product:price:amount'), ('name', 'twitter:data1')]:
            meta = soup.find('meta', {meta_name[0]: meta_name[1]})
            if meta and meta.get('content'):
                val = extract_numeric(meta['content'])
                if val and val > 0:
                    price = val
                    break

    # Priority 4: Twister price data
    if not price:
        for inp in soup.find_all('input', {'id': re.compile(r'twister-plus|price', re.I)}):
            val = inp.get('value')
            if val:
                num = extract_numeric(val)
                if num and num > 0:
                    price = num
                    break

    return price, name

# ──────────────────────────────────────────────
#  Flipkart Scraper & Fetcher
# ──────────────────────────────────────────────

def _fetch_flipkart_with_session(url):
    """
    Fetch Flipkart product page using a persistent session.
    Step 1: visit homepage to obtain real cookies.
    Step 2: fetch the actual product URL with those cookies.
    """
    if not CURL_CFFI_AVAILABLE:
        return safe_fetch(url, use_cffi=False)

    session = cffi_requests.Session()
    base_headers = {
        'Accept-Language': 'en-IN,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    # Warm up: fetch homepage to set cookies
    try:
        session.get('https://www.flipkart.com/', impersonate='chrome120',
                    timeout=15, headers=base_headers)
    except Exception:
        pass

    # Now fetch the actual product page
    r = session.get(url, impersonate='chrome120', timeout=25,
                    headers={**base_headers, 'Referer': 'https://www.flipkart.com/'})
    r.raise_for_status()
    content = r.content
    html_text = content.decode('utf-8', errors='replace')
    return content, html_text, r.status_code

def scrape_flipkart(soup, html_text):
    name = "Unknown Flipkart Product"
    t = soup.find('title')
    if t:
        raw = t.get_text()
        if 'All Categories' in raw or raw.strip() == '':
            return None, name
        name = raw.split('- Buy')[0].split('- Flipkart')[0].strip()

    price = None

    # Layer 1: JSON-LD structured data
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if isinstance(data, dict):
                offers = data.get('offers', {})
                if isinstance(offers, dict) and offers.get('price'):
                    price = float(offers['price'])
                    break
                if isinstance(offers, list):
                    for offer in offers:
                        if offer.get('price'):
                            price = float(offer['price'])
                            break
            if price:
                break
        except Exception:
            pass

    # Layer 2: Current CSS class selectors
    if not price:
        for sel in [
            '._30jeq3', '.Nx9bqj', '._16Jk6d', '._1_WHN1',
            '.CEmiEU', '.hl05eU .Nx9bqj', '.hl05eU',
            '[class*="finalPrice"]', '[class*="selling"]',
        ]:
            el = soup.select_one(sel)
            if el:
                val = extract_numeric(el.get_text())
                if val and val > 10:
                    price = val
                    break

    # Layer 3: Any element whose text is exactly a ₹ price string
    if not price:
        for tag in soup.find_all(['span', 'div', 'p']):
            text = tag.get_text(strip=True)
            if re.match(r'^₹\s?[0-9][0-9,]*$', text):
                val = extract_numeric(text)
                if val and val > 10:
                    price = val
                    break

    # Layer 4: Meta itemprop price
    if not price:
        meta = soup.find('meta', itemprop='price')
        if meta and meta.get('content'):
            price = extract_numeric(meta['content'])

    # Layer 5: Flipkart's embedded React/JSON store
    if not price:
        patterns = [
            r'"finalPrice"\s*:\s*\{[^}]*"value"\s*:\s*(\d+)',
            r'"price"\s*:\s*\{[^}]*"value"\s*:\s*(\d+)',
            r'"discountedPrice"\s*:\s*(\d+)',
            r'"sellingPrice"\s*:\s*(\d+)',
            r'"finalPrice"\s*:\s*(\d+)',
            r'"typedPrice"\s*:\s*(\d+)',
            r'"listingPrice"\s*:\s*(\d+)',
            r'"mrpPrice"\s*:\s*(\d+)',
        ]
        for pat in patterns:
            m = re.search(pat, html_text)
            if m:
                val = float(m.group(1))
                if val > 10:
                    price = val
                    break

    return price, name

# ──────────────────────────────────────────────
#  Myntra, Meesho, Ajio, and Generic Scrapers
# ──────────────────────────────────────────────

def scrape_myntra(content_bytes, html_text):
    soup = BeautifulSoup(content_bytes, 'html.parser')

    name = "Unknown Myntra Product"
    t = soup.find('title')
    if t:
        raw = t.get_text(separator=' ', strip=True)
        name = raw.split(' | ')[0].split('- Buy')[0].replace('Buy ', '').strip()

    price = None

    # 1. JSON-LD structured data
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if isinstance(data, dict):
                offers = data.get('offers', {})
                if isinstance(offers, dict) and offers.get('price'):
                    price = float(offers['price'])
                    break
                if isinstance(offers, list):
                    for offer in offers:
                        if offer.get('price'):
                            price = float(offer['price'])
                            break
                    if price:
                        break
        except Exception:
            pass

    # 2. Regex in raw HTML for Myntra's React store
    if not price:
        for pattern in [
            r'"discountedPrice"\s*:\s*(\d+)',
            r'"price"\s*:\s*(\d+)',
            r'"mrp"\s*:\s*(\d+)',
            r'"sellingPrice"\s*:\s*(\d+)',
        ]:
            m = re.search(pattern, html_text)
            if m:
                val = float(m.group(1))
                if val > 0:
                    price = val
                    break

    # 3. CSS selectors
    if not price:
        for sel in ['.pdp-price strong', '.pdp-discount-container .pdp-price', 'span.pdp-price']:
            el = soup.select_one(sel)
            if el:
                price = extract_numeric(el.get_text())
                if price:
                    break

    return price, name

def scrape_meesho(url, content_bytes, html_text):
    name = "Unknown Meesho Product"
    price = None

    pid_match = re.search(r'/p/([a-zA-Z0-9]+)', url)
    if pid_match and CURL_CFFI_AVAILABLE:
        pid = pid_match.group(1)
        api_url = f'https://www.meesho.com/api/v1/products/{pid}'
        api_headers = {
            'Accept': 'application/json',
            'Referer': url,
            'Origin': 'https://www.meesho.com',
            'Accept-Language': 'en-IN,en;q=0.9',
        }
        try:
            r = cffi_requests.get(api_url, impersonate='chrome120', timeout=15, headers=api_headers)
            if r.status_code == 200:
                data = r.json()
                name = (data.get('name') or data.get('product_name') or
                        data.get('title') or name)
                sp = (data.get('min_price') or data.get('selling_price') or
                      data.get('price') or data.get('mrp'))
                if sp:
                    price = float(sp)
        except Exception:
            pass

    if not price:
        soup = BeautifulSoup(content_bytes, 'html.parser')
        t = soup.find('title')
        if t and t.get_text(strip=True):
            name = t.get_text(strip=True).split('-')[0].strip()

        for pattern in [
            r'"selling_price"\s*:\s*"?(\d+\.?\d*)"?',
            r'"min_price"\s*:\s*"?(\d+\.?\d*)"?',
            r'"price"\s*:\s*"?(\d+\.?\d*)"?',
            r'"mrp"\s*:\s*"?(\d+\.?\d*)"?',
        ]:
            m = re.search(pattern, html_text)
            if m:
                val = float(m.group(1))
                if val > 0:
                    price = val
                    break

    return price, name

def scrape_ajio(soup, html_text):
    name = "Unknown AJIO Product"
    t = soup.find('title')
    if t:
        name = t.get_text().split('|')[0].strip()

    price = None
    for sel in ['.prod-sp', '.price .prod-ptsp', '[class*="price"]']:
        el = soup.select_one(sel)
        if el:
            price = extract_numeric(el.get_text())
            if price:
                break

    if not price:
        for pattern in [r'"price"\s*:\s*"?(\d+\.?\d*)"?', r'"sellingPrice"\s*:\s*"?(\d+\.?\d*)"?']:
            m = re.search(pattern, html_text)
            if m:
                price = float(m.group(1))
                if price:
                    break
    return price, name

def generic_scrape(soup, html_text):
    name = "Unknown Product"
    t = soup.find('title')
    if t:
        name = t.get_text(strip=True).split('|')[0].split('-')[0].strip()

    price = None
    for attr, val in [('property', 'product:price:amount'), ('itemprop', 'price'), ('name', 'price')]:
        meta = soup.find('meta', {attr: val})
        if meta and meta.get('content'):
            price = extract_numeric(meta['content'])
            if price:
                break

    if not price:
        for sel in ['.price', '.product-price', '.current-price', '.offer-price',
                    '.pdp-price', '#product-price', '[itemprop="price"]',
                    '.selling-price', '.sale-price']:
            el = soup.select_one(sel)
            if el:
                price = extract_numeric(el.get_text())
                if price:
                    break

    if not price:
        for pattern in [r'"price"\s*:\s*"?(\d+\.?\d*)"?', r'"sellingPrice"\s*:\s*"?(\d+\.?\d*)"?']:
            m = re.search(pattern, html_text)
            if m:
                val = float(m.group(1))
                if val > 0:
                    price = val
                    break

    return price, name

# ──────────────────────────────────────────────
#  Main entry point
# ──────────────────────────────────────────────

def get_product_details(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Follow short URLs (amzn.to/amzn.eu)
        if 'amzn.to' in domain or 'amzn.eu' in domain:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                r_head = requests.get(url, allow_redirects=True, timeout=10, headers=headers)
                url = r_head.url
                domain = urlparse(url).netloc.lower()
            except Exception:
                pass

        # Amazon specific handler
        if 'amazon' in domain or 'amzn.' in domain:
            try:
                content, html_text, status = _fetch_amazon_with_session(url)
            except Exception as e:
                return {"success": False, "error": f"Amazon fetch error: {str(e)}"}
            
            soup = BeautifulSoup(content, 'html.parser')
            price, name = scrape_amazon(soup, html_text)
            if price:
                return {"success": True, "product_name": name, "current_price": price}
            else:
                return {"success": False, "error": "Could not extract Amazon price. The product may be out of stock or requires login."}

        # Flipkart & Shopsy specific handler
        if 'flipkart' in domain or 'shopsy' in domain:
            try:
                content, html_text, status = _fetch_flipkart_with_session(url)
            except Exception as e:
                return {"success": False, "error": f"Flipkart fetch error: {str(e)}"}
            soup = BeautifulSoup(content, 'html.parser')
            price, name = scrape_flipkart(soup, html_text)

            if price:
                return {"success": True, "product_name": name, "current_price": price}
            else:
                return {"success": False, "error": "Could not extract Flipkart price. The page may have changed or is blocked."}

        # Myntra, Meesho, AJIO, etc.
        cffi_sites = ['myntra', 'meesho', 'ajio']
        use_cffi = any(s in domain for s in cffi_sites) and CURL_CFFI_AVAILABLE

        content, html_text, status = safe_fetch(url, use_cffi=use_cffi, impersonate='chrome120')
        soup = BeautifulSoup(content, 'html.parser')

        price = None
        name = "Unknown Product"

        if 'myntra' in domain:
            price, name = scrape_myntra(content, html_text)
        elif 'meesho' in domain:
            price, name = scrape_meesho(url, content, html_text)
        elif 'ajio' in domain:
            price, name = scrape_ajio(soup, html_text)
        else:
            price, name = generic_scrape(soup, html_text)

        if price:
            return {
                "success": True,
                "product_name": name,
                "current_price": price
            }
        else:
            return {
                "success": False,
                "error": "Could not extract price. The site may use heavy dynamic JavaScript rendering or bot protection."
            }

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if hasattr(e, 'response') and e.response else '?'
        if code in [403, 401]:
            return {"success": False, "error": f"Blocked ({code}): Retailer is restricting automated access."}
        return {"success": False, "error": f"HTTP Error {code}"}
    except Exception as e:
        return {"success": False, "error": f"Scraping Error: {str(e)}"}
