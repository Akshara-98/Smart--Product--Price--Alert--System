try:
    from curl_cffi import requests
    r = requests.get('https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4', impersonate="chrome110", timeout=10)
    print("curl_cffi status:", r.status_code, "len:", len(r.text))
    if r.status_code == 200:
        import re
        prices = re.findall(r'₹[0-9,]+', r.text)
        print("curl_cffi prices:", prices[:5])
except Exception as e:
    print("curl_cffi error:", e)

try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    r = scraper.get('https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4')
    print("cloudscraper status:", r.status_code, "len:", len(r.text))
    if r.status_code == 200:
        import re
        prices = re.findall(r'₹[0-9,]+', r.text)
        print("cloudscraper prices:", prices[:5])
except Exception as e:
    print("cloudscraper error:", e)
