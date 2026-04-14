from processor import BrainProcessor
import os
import json

def test_ai():
    print("Testing AI Connection...")
    processor = BrainProcessor()
    print(f"Provider: {processor.provider}")
    print(f"Proxy defined: {bool(processor.proxy)}")
    
    test_cases = [
        "Remember to buy milk tomorrow at 5pm",
        "Meeting with Sasha on Friday at 10:00 about the new project",
        "Привет, как дела?", # Testing greeting fallback
        "Write a blog post about AI in 2026", # Idea
    ]

    for text in test_cases:
        print(f"\n--- Testing: '{text}' ---")
        try:
            result = processor.classify_and_process(text)
            print("AI Result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error testing AI: {e}")

if __name__ == "__main__":
    test_ai()
