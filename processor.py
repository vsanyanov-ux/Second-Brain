import os
import json
import datetime
from openai import OpenAI
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
import re
import httpx

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

    def _fetch_url_title(self, url):
        """Fetches the title of a web page."""
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code == 200:
                    title_match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        return title_match.group(1).strip()
        except Exception as e:
            print(f"Error fetching URL title: {e}")
        return None

    def classify_and_process(self, text):
        """
        Classifies incoming text into: Task, Note, or Resource.
        Returns a dictionary with classification, title, summary, and tags.
        """
        # Search for URL in text
        url_match = re.search(r'(https?://\S+)', text)
        url = url_match.group(0) if url_match else None
        real_title = self._fetch_url_title(url) if url else None

        context_info = ""
        if real_title:
            context_info = f"\nContextual Title from Link: {real_title}"

        prompt = f"""
        Analyze the following input for a 'Second Brain' system:
        "{text}"
        {context_info}
        
        Classify it into one of these categories:
        1. Task: Something that needs to be done.
        2. Note: A thought, idea, or information to remember.
        3. Resource: A link, book, or reference material.
        4. Event: A meeting, appointment, or event with a specific date/time.
        
        Rules for Extraction:
        - **URL**: Extract the exact URL and put it in the "url" field.
        - **Title**: 
          - Use the 'Contextual Title from Link' if provided to make the title precise.
          - If it's a YouTube link, ensure the title reflects the specific video content.
          - Do NOT use generic prefixes like "YouTube Video:" or "Link:".
          - Do NOT use "Second Brain" as the title.
        - **Summary**: A concise 1-sentence summary of the content.
        - **Date/Time** (for Events): 
          - Current local time is: {datetime.datetime.now().isoformat()}
          - Extract start_time in ISO 8601 format (e.g. YYYY-MM-DDTHH:MM:SS).
          - If the year is not specified, assume current year.
          - If time is not specified for an event, assume 12:00 PM.
        
        Provide the output as JSON:
        {{
            "category": "Task|Note|Resource|Event",
            "title": "Precise Title",
            "summary": "Concise summary",
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
                    {"role": "system", "content": "You are a helpful assistant for a Second Brain system. Your job is to classify and summarize inputs."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
            
        elif self.provider == "mistral" and self.api_key:
            try:
                llm = ChatMistralAI(
                    model="mistral-large-latest",
                    temperature=0,
                    mistral_api_key=self.api_key
                )
                # Mistral doesn't support 'response_format' in the same way, 
                # so we might need to parse the response manually if it's not JSON
                response = llm.invoke(prompt)
                content = response.content
                
                # Robust JSON extraction
                try:
                    # Look for JSON block if AI wrapped it in markdown
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "{" in content:
                        content = content[content.find("{"):content.rfind("}")+1]
                    return json.loads(content)
                except Exception:
                    # Fallback to simple structure
                    return {
                        "category": "Note",
                        "title": real_title if real_title else text[:50],
                        "summary": content[:200],
                        "url": url if url else "",
                        "tags": ["mistral-fallback"]
                    }
            except Exception as e:
                print(f"Error calling Mistral: {e}")
                return {
                    "category": "Note",
                    "title": text[:50] + "...",
                    "summary": f"Mistral error: {str(e)}",
                    "tags": ["error"]
                }
        else:
            # Fallback for no API key or unknown providers
            return {
                "category": "Note",
                "title": text[:50] + "...",
                "summary": text,
                "tags": ["uncategorized"],
                "priority": "Medium"
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
