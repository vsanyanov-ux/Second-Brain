from processor import BrainProcessor
import os

def test_ai():
    print("Testing AI Connection...")
    processor = BrainProcessor()
    print(f"Provider: {processor.provider}")
    print(f"Proxy: {processor.proxy}")
    
    test_text = "Remember to buy milk tomorrow at 5pm"
    try:
        result = processor.classify_and_process(test_text)
        print("Success! AI Result:")
        print(result)
    except Exception as e:
        print(f"Error testing AI: {e}")

if __name__ == "__main__":
    test_ai()
