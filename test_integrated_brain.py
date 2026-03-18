from processor import BrainProcessor
import os
from dotenv import load_dotenv

load_dotenv()

def test_ai_logic():
    bp = BrainProcessor()
    
    # Test cases from the 2026 guide
    test_inputs = [
        "Meet with Sergey about the contract tomorrow at 5pm",
        "How to build a garden fence https://www.thespruce.com/build-your-own-fence-1824707",
        "Buy a new laptop next week",
        "I met Elena today, she is a designer from Berlin"
    ]
    
    print("--- Testing Integrated AI Logic ---")
    for inp in test_inputs:
        print(f"\nProcessing: {inp}")
        result = bp.classify_and_process(inp)
        print(f" Category: {result.get('category')}")
        print(f" Confidence: {result.get('confidence')}")
        print(f" Title: {result.get('title')}")
        print(f" Next Action: {result.get('next_action')}")
        print(f" Summary: {result.get('summary')}")
        if result.get('url'):
            print(f" URL: {result.get('url')}")

if __name__ == "__main__":
    test_ai_logic()
