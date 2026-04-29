import feedparser
import requests
import json
import datetime
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Groq cloud API
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# Absolute path — works regardless of working directory
ALERTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "admin_alerts.json"
)

def fetch_and_classify_updates():
    print("🔍 Scanning for legislative updates...")
    
    # Example: A standard RSS feed for legal/news updates
    # (You can swap this with specific state gazette RSS feeds if available)
    rss_url = "https://prsindia.org/billtrack.xml" # Example URL
    feed = feedparser.parse(rss_url)
    
    new_alerts = []

    # Check the 5 most recent legislative updates
    for entry in feed.entries[:5]:
        title = entry.title
        # Clean up HTML tags if present
        summary = getattr(entry, 'summary', None) or getattr(entry, 'description', '') or ''
        
        print(f"Analyzing: {title}")

        # The NLP Classifier Prompt
        prompt = f"""
        You are an expert Indian Legal AI. Read the following legislative update.
        Does this update relate to:
        1. Rent Control, Tenancy, or Property Leases
        2. Employment, Labour Law, or Wages
        
        Update Title: {title}
        Summary: {summary}

        If it relates to either of these categories, reply with EXACTLY 'YES', followed by the category, and a 1-sentence summary of what changed. 
        If it does NOT relate to these categories, reply with EXACTLY 'NO'.
        """

        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
            )
            llm_reply = response.choices[0].message.content.strip()

            if llm_reply.startswith("YES"):
                print(f"🚨 RELEVANT LAW DETECTED: {title}")
                new_alerts.append({
                    "date_detected": str(datetime.date.today()),
                    "title": title,
                    "link": entry.link,
                    "ai_analysis": llm_reply,
                    "status": "PENDING_ADMIN_APPROVAL"
                })
        except Exception as e:
            print(f"Error communicating with Groq API: {e}")

    # Save alerts for the React Admin Dashboard to read
    if new_alerts:
        # Load existing alerts if the file exists
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r") as f:
                try:
                    existing_alerts = json.load(f)
                except json.JSONDecodeError:
                    existing_alerts = []
        else:
            existing_alerts = []
            
        existing_alerts.extend(new_alerts)
        
        with open(ALERTS_FILE, "w") as f:
            json.dump(existing_alerts, f, indent=4)
        print(f"✅ Saved {len(new_alerts)} new alerts to the Admin Dashboard.")
    else:
        print("✅ No relevant updates found today.")

if __name__ == "__main__":
    fetch_and_classify_updates()