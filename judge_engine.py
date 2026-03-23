"""
judge_engine.py — Legal Judge Engine with IRAC + Citation Verification
Nyaya-Setu | Team IKS | SPIT CSE 2025-26
"""

import os, sys, json, re
sys.path.append(os.path.dirname(__file__))

import ollama
from dotenv import load_dotenv
from gpu_utils import DEVICE
from lex_validator import verify_citations, format_irac

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
KB_PATH      = os.path.join(os.path.dirname(__file__), "data", "legal_kb.json")


# ── Load knowledge base ────────────────────────────────────────────────────────
def load_kb() -> list[dict]:
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["offences"]

KB = load_kb()


# ── Match offences ────────────────────────────────────────────────────────────
def match_offences(text: str) -> list[dict]:
    text_lower = text.lower()
    scored     = []
    for offence in KB:
        score = sum(1 for kw in offence["keywords"] if kw in text_lower)
        if score > 0:
            scored.append((score, offence))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [o for _, o in scored[:3]]


def format_kb_context(offences: list[dict]) -> str:
    if not offences:
        return "No specific offence matched — use general Indian criminal law knowledge."
    parts = []
    for o in offences:
        extra = f"\n  Additional remedy: {o['additional_remedy']}" if o.get("additional_remedy") else ""
        parts.append(
            f"OFFENCE: {o['offence_name']}\n"
            f"  Section: {o['bns_section']}\n"
            f"  Description: {o['description']}\n"
            f"  Punishment: {o['punishment']}\n"
            f"  Cognizable: {'Yes' if o['cognizable'] else 'No'} | "
            f"Bailable: {'Yes' if o['bailable'] else 'No'}\n"
            f"  Triable by: {o['triable_by']}"
            f"{extra}"
        )
    return "\n\n".join(parts)


# ── LLM call ──────────────────────────────────────────────────────────────────
def call_llm(messages: list[dict]) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={
            "temperature": 0.3,
            "num_ctx":     4096,
            "num_gpu":     99,
            "num_thread":  4,
        },
    )
    return response["message"]["content"].strip()


# ── System prompt ─────────────────────────────────────────────────────────────
def build_system_prompt(kb_context: str) -> str:
    return f"""You are Nyaya-Setu, an Indian legal assistant under BNS 2023, BNSS 2023, BSA 2023.

YOUR ROLE:
Give clear legal guidance. Act like a knowledgeable legal advisor — not a court.

CONVERSATION RULES:
- Ask ONE short follow-up question at a time
- Never ask more than one question per message
- Keep messages SHORT — maximum 5 lines while questioning
- Once you have: what happened, who did it, any injury/loss, any evidence → give judgement immediately
- After 5 turns give judgement even if not all facts known

JUDGEMENT FORMAT (use exactly this):
⚖️ Legal Assessment

Section: [exact section from the law provided below]
Offence: [name]
Punishment: [range]
Type: [Cognizable/Non-cognizable] | [Bailable/Non-bailable]

Case strength: [Strong/Moderate/Weak]
Reason: [one sentence]

IRAC Analysis:
Issue: [what legal wrong occurred]
Rule: [what the section says]
Application: [how facts fit the rule]
Conclusion: [likely outcome]

Steps:
1. [specific action]
2. [specific action]
3. [specific action]

RULES:
- Only cite sections from the law provided below
- Never invent section numbers
- No dividers (---), no bullet walls
- After judgement ask: Do you have evidence to attach?

RELEVANT LAW:
{kb_context}"""


# ── JudgeEngine ───────────────────────────────────────────────────────────────
class JudgeEngine:

    def __init__(self):
        self.messages:        list[dict] = []
        self.kb_context:      str        = ""
        self.matched_offences: list[dict] = []
        self.judgement_given: bool       = False
        self.judgement_text:  str        = ""
        self.turn_count:      int        = 0
        self.case_facts:      list[str]  = []

    def start(self, initial_complaint: str) -> str:
        self.matched_offences = match_offences(initial_complaint)
        self.kb_context       = format_kb_context(self.matched_offences)
        self.case_facts.append(initial_complaint)

        system = build_system_prompt(self.kb_context)
        self.messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": initial_complaint},
        ]
        self.turn_count = 1
        reply = call_llm(self.messages)
        self.messages.append({"role": "assistant", "content": reply})
        self._check_judgement(reply)
        return reply

    def reply(self, user_message: str) -> str:
        self.case_facts.append(user_message)
        self.messages.append({"role": "user", "content": user_message})
        self.turn_count += 1

        # Force judgement after 5 turns
        if self.turn_count >= 5 and not self.judgement_given:
            self.messages.append({
                "role":    "system",
                "content": "You have enough information. Give the final judgement NOW using the exact judgement format. Do not ask more questions."
            })

        reply = call_llm(self.messages)
        self.messages.append({"role": "assistant", "content": reply})
        self._check_judgement(reply)
        return self._post_process(reply)

    def _check_judgement(self, reply: str):
        if "⚖️" in reply or "Legal Assessment" in reply or "Case strength" in reply:
            self.judgement_given = True
            self.judgement_text  = reply
            # Run citation verifier on the judgement
            self._verify_judgement_citations(reply)

    def _verify_judgement_citations(self, judgement_text: str):
        """Extract and verify citations in the judgement."""
        sections = re.findall(
            r'(?:BNS|BNSS|BSA)\s+(?:Section\s+)?\d+[A-Z]?(?:\(\d+\))?',
            judgement_text
        )
        if sections:
            result = verify_citations(sections)
            if not result["all_verified"]:
                print(f"[CITATION] Unverified sections: {result['unverified']}")
            else:
                print(f"[CITATION] All {len(sections)} citations verified ✓")

    def _post_process(self, reply: str) -> str:
        """Clean up reply — remove excessive formatting."""
        # Remove triple dashes
        reply = re.sub(r'\n?-{3,}\n?', '\n', reply)
        # Remove excessive blank lines
        reply = re.sub(r'\n{3,}', '\n\n', reply)
        return reply.strip()

    def has_judgement(self) -> bool:
        return self.judgement_given

    def get_summary(self) -> str:
        """One-line case summary for evidence certificate."""
        if self.case_facts:
            return self.case_facts[0][:200]
        return "Legal case via Nyaya-Setu"

    def get_irac(self) -> str:
        """Generate standalone IRAC analysis after judgement."""
        if not self.judgement_given or not self.matched_offences:
            return ""
        offence    = self.matched_offences[0]
        case_facts = " ".join(self.case_facts[:3])
        return format_irac(
            complaint=self.case_facts[0] if self.case_facts else "",
            section=offence["bns_section"],
            section_desc=offence["description"],
            punishment=offence["punishment"],
            case_facts=case_facts,
        )


# ── Singleton store ───────────────────────────────────────────────────────────
_engines: dict[str, JudgeEngine] = {}

def get_judge(phone: str) -> JudgeEngine:
    if phone not in _engines:
        _engines[phone] = JudgeEngine()
    return _engines[phone]

def reset_judge(phone: str):
    if phone in _engines:
        del _engines[phone]


# ── CLI test ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Nyaya-Setu Judge Engine — Interactive Test")
    print("Type 'quit' to exit\n")

    engine    = JudgeEngine()
    complaint = input("Describe your problem: ").strip()
    reply     = engine.start(complaint)
    print(f"\nBot: {reply}\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break
        reply = engine.reply(user_input)
        print(f"\nBot: {reply}\n")
        if engine.has_judgement():
            print("--- Judgement given ---\n")