import os
import json
from openai import OpenAI
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

load_dotenv()

class BrainProcessor:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        self.proxy = os.getenv("SOCKS5_PROXY") # e.g. "socks5://127.0.0.1:1080"
        
        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "mistral":
            self.api_key = os.getenv("MISTRAL_API_KEY")
            # Mistral client will be initialized per-request to manage proxy environment vars
            self.client = None
        else:
            self.client = None

    def classify_and_process(self, text):
        """
        Classifies incoming text into: Task, Note, or Resource.
        Returns a dictionary with classification, title, summary, and tags.
        """
        prompt = f"""
        Analyze the following input for a 'Second Brain' system:
        "{text}"
        
        Classify it into one of these categories:
        1. Task: Something that needs to be done.
        2. Note: A thought, idea, or information to remember.
        3. Resource: A link, book, or reference material.
        
        Provide the output in the following JSON format:
        {{
            "category": "Task|Note|Resource",
            "title": "A short, descriptive title",
            "summary": "A 1-sentence summary",
            "tags": ["tag1", "tag2"],
            "priority": "High|Medium|Low" (if Task)
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
            # Apply proxy if configured
            if self.proxy:
                os.environ["HTTP_PROXY"] = self.proxy
                os.environ["HTTPS_PROXY"] = self.proxy
                os.environ["ALL_PROXY"] = self.proxy
            
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
                        "title": text[:50],
                        "summary": content[:200],
                        "tags": ["mistral-fallback"]
                    }
            finally:
                # Clean up environment
                if self.proxy:
                    os.environ.pop("HTTP_PROXY", None)
                    os.environ.pop("HTTPS_PROXY", None)
                    os.environ.pop("ALL_PROXY", None)
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
