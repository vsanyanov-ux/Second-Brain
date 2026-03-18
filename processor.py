import os
import json
import datetime
import re
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

load_dotenv()

class BrainProcessor:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        
        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "mistral":
            self.api_key = os.getenv("MISTRAL_API_KEY")
            self.client = None
        else:
            self.client = None

    def _fetch_url_content(self, url):
        """Fetches the title and main content of a web page."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Get Title
                    title = soup.title.string.strip() if soup.title else None
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Get text from body
                    body_text = soup.get_text()
                    # Clean up whitespace
                    lines = (line.strip() for line in body_text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    clean_text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return {
                        "title": title,
                        "content": clean_text[:2000] # Limit content for AI processing
                    }
        except Exception as e:
            print(f"Error fetching URL content: {e}")
        return None

    def classify_and_process(self, text):
        """
        Classifies incoming text into: Project, Idea, Person, Admin, or Event.
        Used the 'Second Brain 2026' architecture for extraction.
        """
        # Search for URL in text
        url_match = re.search(r'(https?://\S+)', text)
        url = url_match.group(0) if url_match else None
        
        web_data = self._fetch_url_content(url) if url else None
        
        context_info = ""
        if web_data:
            context_info = f"\nWeb Page Title: {web_data.get('title')}\nWeb Page Content Summary: {web_data.get('content', '')[:1500]}"

        prompt = f"""
        Analyze the following input for a 'Second Brain' system based on the 2026 Architecture:
        "{text}"
        {context_info}
        
        Classify it into one of these categories:
        1. Project: A concrete objective with a next step (Tasks belong here).
        2. Idea: A thought, insight, or interesting reference/link to save for later.
        3. Person: Information about someone (contact info, context of meeting).
        4. Admin: Bureaucracy, payments, logistics, or non-creative maintenance tasks.
        5. Event: A meeting or appointment with a specific date/time.
        
        Rules for Extraction:
        - **Confidence**: Rate your confidence in this classification from 0.0 to 1.0.
        - **Title**: Create a precise, punchy title.
        - **Summary**: A concise 1-sentence summary of the core essence.
        - **Next Action** (For Projects/Admin): What is the single literal next step?
        - **Context** (For People): How do we know them? What to discuss next?
        - **URL**: Extract the exact URL if present.
        - **Date/Time** (for Events): 
          - Current local time is: {datetime.datetime.now().isoformat()}
          - Extract start_time in ISO 8601 format.
        
        Provide the output as JSON:
        {{
            "category": "Project|Idea|Person|Admin|Event",
            "confidence": 0.0,
            "title": "Precise Title",
            "summary": "Concise summary",
            "next_action": "Single next step",
            "context": "Person context",
            "url": "full_url_here",
            "tags": ["relevant", "tags"],
            "priority": "High|Medium|Low",
            "start_time": "ISO_DATETIME_HERE",
            "end_time": "ISO_DATETIME_HERE"
        }}
        """
        
        if self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional Second Brain Librarian. You categorize information with high precision."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
            
        elif self.provider == "mistral" and self.api_key:
            try:
                llm = ChatMistralAI(model="mistral-large-latest", temperature=0, mistral_api_key=self.api_key)
                response = llm.invoke(prompt)
                content = response.content
                
                # Robust JSON extraction
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "{" in content:
                    content = content[content.find("{"):content.rfind("}")+1]
                return json.loads(content)
            except Exception as e:
                print(f"Error calling Mistral: {e}")
                return self._fallback_response(text, url, web_data)
        else:
            return self._fallback_response(text, url, web_data)

    def _fallback_response(self, text, url, web_data):
        return {
            "category": "Idea",
            "confidence": 0.5,
            "title": web_data['title'] if web_data and web_data.get('title') else text[:50],
            "summary": text,
            "next_action": "",
            "context": "",
            "url": url if url else "",
            "tags": ["uncategorized"],
            "priority": "Medium",
            "start_time": "",
            "end_time": ""
        }

    def transcribe_voice(self, file_path):
        """Transcribes voice messages using Whisper."""
        if self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
                return transcript.text
        return "Voice transcription not available (requires OpenAI provider)."
