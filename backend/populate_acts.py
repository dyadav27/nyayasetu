import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import StatutoryAct
from document_analyzer import fetch_acts
import time

CATEGORIES = [
    "All", "Agriculture & Rural", "Banking & Finance", "Civil Procedure",
    "Constitutional Law", "Contract & Commercial", "Corporate & Company Law",
    "Criminal Law", "Criminal Law (2023)", "Cyber & Technology",
    "Dispute Resolution", "Education Law", "Elections & Voting",
    "Environment & Energy", "Family & Personal Law", "Health & Medicine",
    "Human Rights", "Intellectual Property", "Labor & Employment",
    "Property & Land", "Taxation & Revenue", "Transportation & Logistics"
]

JURISDICTIONS = [
    "Union of India", "State of Maharashtra", "State of Rajasthan", "State of Tamilnadu- Act",
    "State of Punjab", "State of Uttar Pradesh", "State of Madhya Pradesh", "State of Odisha",
    "State of Bihar", "State of Andhra Pradesh", "State of Haryana",
    "State of West Bengal", "State of Gujarat", "State of Jammu-Kashmir", "State of Assam",
    "State of Karnataka", "State of Jharkhand", "State of Goa", "State of Telangana",
    "State of Chattisgarh", "NCT Delhi", "State of Himachal Pradesh", "State of Kerala"
]

db = SessionLocal()

def scrape():
    for jurisdiction in JURISDICTIONS:
        act_type = "central"
        state_name = ""
        if jurisdiction.startswith("State of"):
            act_type = "state"
            raw_state = jurisdiction.replace("State of", "").strip()
            state_name = raw_state.split("-")[0].strip()

        # For states, Kanoon's search by category isn't very reliable, but we'll try the first few.
        categories_to_fetch = ["All"] if act_type == "state" else CATEGORIES
        
        print(f"\n=== Fetching for {jurisdiction} ===")
        for category in categories_to_fetch:
            query = category if category != "All" else ""
            print(f" -> Category: {category}")
            
            # Fetch all pages until Indian Kanoon returns no more results
            for pagenum in range(500):
                print(f"    Page {pagenum} ...")
                try:
                    acts = fetch_acts(query=query, act_type=act_type, state_name=state_name, pagenum=pagenum)
                    if not acts:
                        break
                    
                    added_count = 0
                    for a in acts:
                        existing = db.query(StatutoryAct).filter(StatutoryAct.doc_id == a["doc_id"]).first()
                        if not existing:
                            new_act = StatutoryAct(
                                title=a["title"],
                                summary=a["summary"],
                                jurisdiction=jurisdiction,
                                category=category,
                                year=a["year"],
                                url=a["url"],
                                doc_id=a["doc_id"],
                                act_type=act_type
                            )
                            db.add(new_act)
                            added_count += 1
                        else:
                            # Append category if not already in it
                            if category not in existing.category:
                                existing.category += f", {category}"
                                
                    db.commit()
                    print(f"      Saved {added_count} new acts.")
                    
                    if len(acts) < 10:
                        break # End of results
                    
                    time.sleep(1) # rate limit protection
                    
                except Exception as e:
                    print(f"Error: {e}")
                    break

if __name__ == "__main__":
    scrape()
    print("Scraping complete.")
