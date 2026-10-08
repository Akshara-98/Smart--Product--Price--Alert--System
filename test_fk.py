import requests
import re
urls = ["https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"]

headers1 = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
headers2 = {"User-Agent": "curl/7.81.0", "Accept": "*/*"}
headers3 = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

for idx, h in enumerate([headers1, headers2, headers3]):
    print(f"\n--- Testing Headers {idx+1} ---")
    try:
        r = requests.get(urls[0], headers=h, timeout=10)
        print("Status:", r.status_code, "Length:", len(r.text))
        if r.status_code == 200:
            prices = re.findall(r'₹[0-9,]+', r.text)
            print("Found prices:", prices[:5])
    except Exception as e:
        print(e)
