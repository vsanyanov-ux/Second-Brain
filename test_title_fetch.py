import re
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def test_fetch(url, proxy=None):
    print(f"Testing URL: {url}")
    print(f"Using Proxy: {proxy}")
    try:
        proxies = {"all://": proxy} if proxy else None
        with httpx.Client(proxy=proxy, timeout=10.0, follow_redirects=True) as client:
            response = client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                title_match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
                if title_match:
                    print(f"Found Title: {title_match.group(1).strip()}")
                else:
                    print("No <title> tag found in response.")
            else:
                print(f"Error Response: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    url = "https://youtu.be/MmTwYkNTH-E?si=zacaBZbfvdQ2GE9j"
    proxy = os.getenv("SOCKS5_PROXY")
    test_fetch(url, proxy)
