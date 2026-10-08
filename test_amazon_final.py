import scraper
import os

# Test URLs that were previously failing
test_urls = [
    "https://www.amazon.co.uk/dp/B0CHX1W1XY",
    "https://amzn.to/3PskXG8", # Example short link (fake but for validation)
    "https://amazon.de/dp/B0CHX1W1XY",
    "https://www.amazon.in/dp/B0CHX1W1XY"
]

print("--- Testing Updated URL Validation ---")
for url in test_urls:
    res = scraper.is_supported_url(url)
    print(f"{url}: {'VALID' if res else 'INVALID'}")

print("\n--- Testing Logic Check (CFFI check) ---")
# Check get_product_details logic internally (mocking external calls if needed)
# For now, just check if 'amazon' in domain triggers use_cffi 
domain = "www.amazon.co.uk"
cffi_sites = ['amazon', 'flipkart', 'shopsy', 'myntra', 'meesho', 'ajio']
use_cffi = any(s in domain for s in cffi_sites)
print(f"Domain '{domain}' uses CFFI: {use_cffi}")
