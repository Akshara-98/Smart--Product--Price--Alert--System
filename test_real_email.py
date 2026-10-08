import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import notifier

# Test 1: Send to alertprice@gmail.com (user's email from DB)
print("=== TEST 1: Sending to alertprice@gmail.com ===")
result1 = notifier.send_price_alert(
    user_email="alertprice@gmail.com",
    product_name="Test Watch",
    current_price=500.0,
    target_price=600.0,
    product_url="https://www.flipkart.com/test"
)
print(f"Result: {'SUCCESS' if result1 else 'FAILED'}")

# Test 2: Send to aksharakatakam261@gmail.com
print("\n=== TEST 2: Sending to aksharakatakam261@gmail.com ===")
result2 = notifier.send_price_alert(
    user_email="aksharakatakam261@gmail.com",
    product_name="Test Kurta",
    current_price=800.0,
    target_price=900.0,
    product_url="https://www.myntra.com/test"
)
print(f"Result: {'SUCCESS' if result2 else 'FAILED'}")
