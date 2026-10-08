import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import scraper

test_cases = [
    ("Amazon",   "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX2F5QT"),
    ("Flipkart", "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"),
    ("Myntra",   "https://www.myntra.com/tshirts/roadster/roadster-men-black-cotton-pure-cotton-t-shirt/2275365/buy"),
    ("Meesho",   "https://www.meesho.com/elegant-men-tshirts/p/2z8g6e"),
]

# Test URL validation
print("=== URL Validation Tests ===")
valid_urls = [
    "https://www.amazon.in/dp/B0CHX2F5QT",
    "https://www.flipkart.com/some-product/p/abc",
    "https://www.myntra.com/shirts/123",
    "https://www.meesho.com/product/p/xyz",
    "https://www.ajio.com/product",
    "https://www.nykaa.com/product",
]
invalid_urls = [
    "https://www.google.com/search?q=phone",
    "https://www.ebay.com/item/123",
    "https://www.olx.in/item/abc",
    "not-a-url",
]

for u in valid_urls:
    ok = scraper.is_supported_url(u)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] VALID expected:   {u[:60]}")

for u in invalid_urls:
    ok = scraper.is_supported_url(u)
    status = "PASS" if not ok else "FAIL"
    print(f"  [{status}] INVALID expected: {u[:60]}")

print()
print("=== Scraper Tests ===")
for site, url in test_cases:
    print(f"\n>> {site}")
    print(f"   URL: {url[:80]}")
    result = scraper.get_product_details(url)
    if result['success']:
        print(f"   Name:  {result['product_name'][:70]}")
        print(f"   Price: Rs.{result['current_price']}")
    else:
        print(f"   ERROR: {result['error']}")
