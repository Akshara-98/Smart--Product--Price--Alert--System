import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from curl_cffi import requests as cffi_requests
import json, re

pid = '2z8g6e'
product_url = f'https://www.meesho.com/elegant-men-tshirts/p/{pid}'

# Meesho mobile/prism API headers (Android app style)
mobile_headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-App-Version-Code': '310',
    'X-Device-Id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    'X-App-Name': 'meesho',
    'X-Platform': 'android',
    'Accept-Language': 'en-IN',
    'Referer': product_url,
}

endpoints = [
    ('GET',  f'https://prism.meesho.com/api/v1/supplier_listings/{pid}'),
    ('GET',  f'https://prism.meesho.com/api/v2/supplier_listings/{pid}'),
    ('GET',  f'https://prism.meesho.com/api/v1/products/{pid}'),
    ('GET',  f'https://www.meesho.com/api/v1/supplier_listings/{pid}'),
    ('GET',  f'https://www.meesho.com/api/v2/supplier_listings/{pid}'),
    ('POST', 'https://prism.meesho.com/api/v1/pdps', {"supplier_listing_id": pid}),
    ('POST', 'https://prism.meesho.com/api/v2/pdps', {"slug": f"elegant-men-tshirts/p/{pid}"}),
]

for method, url, *body in endpoints:
    try:
        if method == 'GET':
            r = cffi_requests.get(url, impersonate='chrome120', timeout=8, headers=mobile_headers)
        else:
            r = cffi_requests.post(url, json=body[0] if body else {}, impersonate='chrome120', timeout=8, headers=mobile_headers)
        
        ctype = r.headers.get('content-type', '')
        print(f'[{method}] {url}')
        print(f'  status={r.status_code}, len={len(r.text)}, ct={ctype[:40]}')
        if r.status_code == 200:
            if 'json' in ctype:
                data = r.json()
                print(f'  JSON keys: {list(data.keys())[:10]}')
                print(f'  data: {str(data)[:400]}')
            else:
                print(f'  body: {r.text[:200]}')
        print()
    except Exception as e:
        print(f'[{method}] {url} -> ERROR: {e}\n')
