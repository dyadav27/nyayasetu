"""
alji.py — Automatic Legal Jurisdiction Identification  v2.0
NyayaSetu | Team IKS | SPIT CSE 2025-26

Detects which Indian state's laws govern an uploaded document by reading
location signals from the document text itself. No GPU needed — runs
entirely on CPU.

v2.0 changes over v1:
  - All regexes pre-compiled at module load (no per-call re-compile overhead)
  - SORTED_CITIES pre-sorted once at load (not on every _extract_cities call)
  - Multi-signal consensus scoring: agreeing signals boost confidence
  - Broader conflict detection: PIN vs city disagreement also flagged
  - Fixed data errors: Raipur → Chhattisgarh, Chandigarh UT handling
  - Expanded PIN prefix table to cover CG, Uttarakhand, all NE states, UTs
  - Expanded city gazetteer: Chhattisgarh, Uttarakhand, all NE states, UTs
  - New document types: sale_deed, affidavit, mou, nda, will_testament
  - Law matrix entries for all new document types
  - Cleaner, consistent signal-priority logic

Usage:
    from alji import detect_jurisdiction, get_law_framework, get_rag_context

    result = detect_jurisdiction(text)
    print(result)
    # {
    #   "state": "Maharashtra",
    #   "confidence": 0.95,
    #   "signal_used": "stamp_paper",
    #   "signals_found": [...],
    #   "doc_type": "rental_agreement",
    #   "laws": {...},
    #   "conflict": None,
    #   "transparency": "..."
    # }
"""

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1. PIN CODE → STATE
#    India Post postal circles — first 2 digits identify the circle,
#    which maps 1-to-1 with a state/UT in almost all cases.
#    FIX v2: Added Chhattisgarh (49x), Uttarakhand (24x overlap resolved),
#    all NE states (78–79x), Andaman (74x), Lakshadweep (67x partial).
# ─────────────────────────────────────────────────────────────────────────────
PIN_PREFIX_TO_STATE: dict[str, str] = {
    "11": "Delhi",
    "12": "Haryana", "13": "Haryana",
    "14": "Punjab",  "15": "Punjab",  "16": "Punjab",
    "17": "Himachal Pradesh",
    "18": "Jammu and Kashmir", "19": "Jammu and Kashmir",
    "20": "Uttar Pradesh", "21": "Uttar Pradesh", "22": "Uttar Pradesh",
    "23": "Uttar Pradesh", "24": "Uttarakhand",   "25": "Uttar Pradesh",
    "26": "Uttar Pradesh", "27": "Uttar Pradesh", "28": "Uttar Pradesh",
    "30": "Rajasthan", "31": "Rajasthan", "32": "Rajasthan",
    "33": "Rajasthan", "34": "Rajasthan",
    "36": "Gujarat",   "37": "Gujarat",   "38": "Gujarat",   "39": "Gujarat",
    "40": "Maharashtra", "41": "Maharashtra", "42": "Maharashtra",
    "43": "Maharashtra", "44": "Maharashtra", "45": "Maharashtra",
    "46": "Maharashtra", "47": "Maharashtra",
    "48": "Madhya Pradesh",
    "49": "Chhattisgarh",          # FIX v2: was MP; 49x is CG circle
    "50": "Telangana",   "51": "Telangana",   "52": "Telangana",
    "53": "Andhra Pradesh", "54": "Andhra Pradesh", "55": "Andhra Pradesh",
    "56": "Karnataka",   "57": "Karnataka",   "58": "Karnataka",
    "59": "Karnataka",
    "60": "Tamil Nadu",  "61": "Tamil Nadu",  "62": "Tamil Nadu",
    "63": "Tamil Nadu",  "64": "Tamil Nadu",  "65": "Tamil Nadu",
    "67": "Kerala",      "68": "Kerala",      "69": "Kerala",
    "70": "West Bengal", "71": "West Bengal", "72": "West Bengal",
    "73": "West Bengal", "74": "West Bengal",
    "75": "Odisha",      "76": "Odisha",      "77": "Odisha",
    "78": "Assam",       "79": "Assam",
    "80": "Bihar",       "81": "Bihar",       "82": "Bihar",
    "83": "Jharkhand",   "84": "Jharkhand",
    "85": "Bihar",
    "86": "Manipur",
    "87": "Nagaland",
    "88": "Manipur",
    "89": "Arunachal Pradesh",
    "90": "Army Post Office",
    "91": "Meghalaya",
    "92": "Tripura",
    "93": "Mizoram",
    "94": "Sikkim",
    "95": "Goa",
    "96": "Goa",
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. CITY / DISTRICT → STATE
#    FIX v2: Added Chhattisgarh cities, Uttarakhand additions,
#    all NE state capitals, Goa additions, Chandigarh mapped to UT.
# ─────────────────────────────────────────────────────────────────────────────
CITY_TO_STATE: dict[str, str] = {
    # ── Maharashtra ──────────────────────────────────────────────────────────
    "mumbai": "Maharashtra", "bombay": "Maharashtra", "pune": "Maharashtra",
    "nagpur": "Maharashtra", "nashik": "Maharashtra", "aurangabad": "Maharashtra",
    "chhatrapati sambhajinagar": "Maharashtra",       # new name for aurangabad
    "thane": "Maharashtra", "solapur": "Maharashtra", "kolhapur": "Maharashtra",
    "navi mumbai": "Maharashtra", "andheri": "Maharashtra", "bandra": "Maharashtra",
    "dadar": "Maharashtra", "worli": "Maharashtra", "borivali": "Maharashtra",
    "mulund": "Maharashtra", "pimpri": "Maharashtra", "chinchwad": "Maharashtra",
    "sangli": "Maharashtra", "satara": "Maharashtra", "ratnagiri": "Maharashtra",
    "amravati": "Maharashtra", "akola": "Maharashtra", "latur": "Maharashtra",
    "jalgaon": "Maharashtra", "dhule": "Maharashtra", "nanded": "Maharashtra",
    "bid": "Maharashtra", "osmanabad": "Maharashtra", "dharashiv": "Maharashtra",

    # ── Delhi ────────────────────────────────────────────────────────────────
    "delhi": "Delhi", "new delhi": "Delhi", "south delhi": "Delhi",
    "north delhi": "Delhi", "east delhi": "Delhi", "west delhi": "Delhi",
    "dwarka": "Delhi", "rohini": "Delhi", "pitampura": "Delhi",
    "saket": "Delhi", "lajpat nagar": "Delhi", "connaught place": "Delhi",
    "janakpuri": "Delhi", "nehru place": "Delhi", "karol bagh": "Delhi",
    "vasant kunj": "Delhi", "mayur vihar": "Delhi", "preet vihar": "Delhi",

    # ── Karnataka ────────────────────────────────────────────────────────────
    "bengaluru": "Karnataka", "bangalore": "Karnataka",
    "mysuru": "Karnataka", "mysore": "Karnataka",
    "hubli": "Karnataka", "dharwad": "Karnataka",
    "mangaluru": "Karnataka", "mangalore": "Karnataka",
    "belagavi": "Karnataka", "belgaum": "Karnataka",
    "gulbarga": "Karnataka", "kalaburagi": "Karnataka",
    "shimoga": "Karnataka", "shivamogga": "Karnataka",
    "tumkur": "Karnataka", "tumakuru": "Karnataka", "udupi": "Karnataka",
    "davanagere": "Karnataka", "ballari": "Karnataka", "bellary": "Karnataka",
    "vijayapura": "Karnataka", "bijapur": "Karnataka",

    # ── Tamil Nadu ───────────────────────────────────────────────────────────
    "chennai": "Tamil Nadu", "madras": "Tamil Nadu",
    "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "trichy": "Tamil Nadu", "tiruchirappalli": "Tamil Nadu",
    "salem": "Tamil Nadu", "tirunelveli": "Tamil Nadu", "vellore": "Tamil Nadu",
    "erode": "Tamil Nadu", "tiruppur": "Tamil Nadu", "thoothukudi": "Tamil Nadu",
    "tuticorin": "Tamil Nadu", "kancheepuram": "Tamil Nadu",
    "chengalpattu": "Tamil Nadu", "cuddalore": "Tamil Nadu",

    # ── Telangana ────────────────────────────────────────────────────────────
    "hyderabad": "Telangana", "secunderabad": "Telangana",
    "warangal": "Telangana", "nizamabad": "Telangana",
    "karimnagar": "Telangana", "khammam": "Telangana",
    "cyberabad": "Telangana", "hitec city": "Telangana",
    "nalgonda": "Telangana", "mahbubnagar": "Telangana",
    "rangareddy": "Telangana",

    # ── Andhra Pradesh ───────────────────────────────────────────────────────
    "visakhapatnam": "Andhra Pradesh", "vizag": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh", "guntur": "Andhra Pradesh",
    "nellore": "Andhra Pradesh", "kurnool": "Andhra Pradesh",
    "tirupati": "Andhra Pradesh", "rajahmundry": "Andhra Pradesh",
    "kakinada": "Andhra Pradesh", "kadapa": "Andhra Pradesh",
    "amaravati": "Andhra Pradesh",

    # ── West Bengal ──────────────────────────────────────────────────────────
    "kolkata": "West Bengal", "calcutta": "West Bengal",
    "howrah": "West Bengal", "durgapur": "West Bengal",
    "asansol": "West Bengal", "siliguri": "West Bengal",
    "darjeeling": "West Bengal", "bardhaman": "West Bengal",
    "burdwan": "West Bengal", "haldia": "West Bengal",
    "kharagpur": "West Bengal", "malda": "West Bengal",

    # ── Gujarat ──────────────────────────────────────────────────────────────
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "baroda": "Gujarat", "rajkot": "Gujarat", "bhavnagar": "Gujarat",
    "jamnagar": "Gujarat", "gandhinagar": "Gujarat", "anand": "Gujarat",
    "mehsana": "Gujarat", "morbi": "Gujarat", "surendranagar": "Gujarat",
    "bharuch": "Gujarat", "navsari": "Gujarat", "vapi": "Gujarat",

    # ── Uttar Pradesh ────────────────────────────────────────────────────────
    "lucknow": "Uttar Pradesh", "noida": "Uttar Pradesh",
    "greater noida": "Uttar Pradesh", "agra": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
    "banaras": "Uttar Pradesh", "allahabad": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh", "meerut": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh", "bareilly": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh", "moradabad": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh", "mathura": "Uttar Pradesh",
    "firozabad": "Uttar Pradesh", "saharanpur": "Uttar Pradesh",

    # ── Uttarakhand  (FIX v2: separated from UP) ─────────────────────────────
    "dehradun": "Uttarakhand", "haridwar": "Uttarakhand",
    "rishikesh": "Uttarakhand", "nainital": "Uttarakhand",
    "roorkee": "Uttarakhand", "haldwani": "Uttarakhand",
    "rudrapur": "Uttarakhand", "kashipur": "Uttarakhand",
    "mussoorie": "Uttarakhand", "almora": "Uttarakhand",
    "pithoragarh": "Uttarakhand",

    # ── Rajasthan ────────────────────────────────────────────────────────────
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan",
    "kota": "Rajasthan", "ajmer": "Rajasthan", "bikaner": "Rajasthan",
    "alwar": "Rajasthan", "bharatpur": "Rajasthan", "sikar": "Rajasthan",
    "pali": "Rajasthan", "barmer": "Rajasthan", "churu": "Rajasthan",

    # ── Madhya Pradesh ───────────────────────────────────────────────────────
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh", "gwalior": "Madhya Pradesh",
    "ujjain": "Madhya Pradesh", "sagar": "Madhya Pradesh",
    "satna": "Madhya Pradesh", "rewa": "Madhya Pradesh",
    "dewas": "Madhya Pradesh", "katni": "Madhya Pradesh",

    # ── Chhattisgarh  (FIX v2: was entirely missing) ─────────────────────────
    "raipur": "Chhattisgarh",      # FIX: was mapped to MP in v1
    "bilaspur": "Chhattisgarh",
    "bhilai": "Chhattisgarh",
    "durg": "Chhattisgarh",
    "korba": "Chhattisgarh",
    "rajnandgaon": "Chhattisgarh",
    "raigarh": "Chhattisgarh",
    "jagdalpur": "Chhattisgarh",
    "ambikapur": "Chhattisgarh",

    # ── Punjab ───────────────────────────────────────────────────────────────
    "ludhiana": "Punjab", "amritsar": "Punjab",
    "jalandhar": "Punjab", "patiala": "Punjab", "bathinda": "Punjab",
    "mohali": "Punjab", "pathankot": "Punjab", "hoshiarpur": "Punjab",

    # ── Chandigarh UT  (FIX v2: separate from Punjab) ────────────────────────
    "chandigarh": "Chandigarh",

    # ── Haryana ──────────────────────────────────────────────────────────────
    "gurugram": "Haryana", "gurgaon": "Haryana", "faridabad": "Haryana",
    "ambala": "Haryana", "panipat": "Haryana", "rohtak": "Haryana",
    "hisar": "Haryana", "karnal": "Haryana", "sonipat": "Haryana",
    "yamunanagar": "Haryana", "panchkula": "Haryana",

    # ── Kerala ───────────────────────────────────────────────────────────────
    "thiruvananthapuram": "Kerala", "trivandrum": "Kerala",
    "kochi": "Kerala", "cochin": "Kerala", "kozhikode": "Kerala",
    "calicut": "Kerala", "thrissur": "Kerala", "kollam": "Kerala",
    "palakkad": "Kerala", "kannur": "Kerala", "malappuram": "Kerala",
    "alappuzha": "Kerala", "alleppey": "Kerala", "kottayam": "Kerala",

    # ── Odisha ───────────────────────────────────────────────────────────────
    "bhubaneswar": "Odisha", "cuttack": "Odisha", "rourkela": "Odisha",
    "berhampur": "Odisha", "sambalpur": "Odisha",
    "balasore": "Odisha", "baripada": "Odisha", "puri": "Odisha",

    # ── Bihar ────────────────────────────────────────────────────────────────
    "patna": "Bihar", "gaya": "Bihar", "bhagalpur": "Bihar",
    "muzaffarpur": "Bihar", "darbhanga": "Bihar",
    "purnia": "Bihar", "arrah": "Bihar", "begusarai": "Bihar",

    # ── Jharkhand ────────────────────────────────────────────────────────────
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand",
    "dhanbad": "Jharkhand", "bokaro": "Jharkhand",
    "hazaribagh": "Jharkhand", "deoghar": "Jharkhand",
    "giridih": "Jharkhand", "dumka": "Jharkhand",

    # ── Assam ────────────────────────────────────────────────────────────────
    "guwahati": "Assam", "dibrugarh": "Assam",
    "silchar": "Assam", "jorhat": "Assam",
    "nagaon": "Assam", "tinsukia": "Assam",
    "dispur": "Assam",   # capital of Assam (part of Guwahati metro)

    # ── NE States  (FIX v2: largely missing in v1) ────────────────────────────
    "imphal": "Manipur",
    "kohima": "Nagaland",
    "dimapur": "Nagaland",
    "shillong": "Meghalaya",
    "aizawl": "Mizoram",
    "lunglei": "Mizoram",
    "agartala": "Tripura",
    "itanagar": "Arunachal Pradesh",
    "gangtok": "Sikkim",

    # ── Himachal Pradesh ─────────────────────────────────────────────────────
    "shimla": "Himachal Pradesh", "manali": "Himachal Pradesh",
    "dharamsala": "Himachal Pradesh", "solan": "Himachal Pradesh",
    "mandi": "Himachal Pradesh", "kangra": "Himachal Pradesh",
    "kullu": "Himachal Pradesh", "hamirpur": "Himachal Pradesh",

    # ── Jammu and Kashmir / Ladakh ───────────────────────────────────────────
    "srinagar": "Jammu and Kashmir", "jammu": "Jammu and Kashmir",
    "leh": "Ladakh", "kargil": "Ladakh",
    "anantnag": "Jammu and Kashmir", "baramulla": "Jammu and Kashmir",

    # ── Goa ──────────────────────────────────────────────────────────────────
    "panaji": "Goa", "panjim": "Goa", "margao": "Goa",
    "vasco": "Goa", "mapusa": "Goa", "ponda": "Goa",
    "bicholim": "Goa", "curchorem": "Goa",
}

# ─────────────────────────────────────────────────────────────────────────────
# PRE-SORTED city list (longest first) — computed ONCE at module load.
# This avoids re-sorting on every _extract_cities() call.
# ─────────────────────────────────────────────────────────────────────────────
_SORTED_CITIES: list[tuple[str, str]] = sorted(
    CITY_TO_STATE.items(), key=lambda x: len(x[0]), reverse=True
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. STAMP PAPER PATTERNS → STATE  (pre-compiled at load)
# ─────────────────────────────────────────────────────────────────────────────
_STAMP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"maharashtra\s+stamp",    re.I), "Maharashtra"),
    (re.compile(r"delhi\s+stamp",          re.I), "Delhi"),
    (re.compile(r"karnataka\s+stamp",      re.I), "Karnataka"),
    (re.compile(r"tamil\s*nadu\s+stamp",   re.I), "Tamil Nadu"),
    (re.compile(r"telangana\s+stamp",      re.I), "Telangana"),
    (re.compile(r"gujarat\s+stamp",        re.I), "Gujarat"),
    (re.compile(r"west\s*bengal\s+stamp",  re.I), "West Bengal"),
    (re.compile(r"uttar\s*pradesh\s+stamp",re.I), "Uttar Pradesh"),
    (re.compile(r"rajasthan\s+stamp",      re.I), "Rajasthan"),
    (re.compile(r"kerala\s+stamp",         re.I), "Kerala"),
    (re.compile(r"punjab\s+stamp",         re.I), "Punjab"),
    (re.compile(r"haryana\s+stamp",        re.I), "Haryana"),
    (re.compile(r"chhattisgarh\s+stamp",   re.I), "Chhattisgarh"),
    (re.compile(r"madhya\s*pradesh\s+stamp", re.I), "Madhya Pradesh"),
    (re.compile(r"andhra\s*pradesh\s+stamp", re.I), "Andhra Pradesh"),
    (re.compile(r"odisha\s+stamp",         re.I), "Odisha"),
    (re.compile(r"jharkhand\s+stamp",      re.I), "Jharkhand"),
    (re.compile(r"bihar\s+stamp",          re.I), "Bihar"),
    (re.compile(r"stamp\s+paper.*?maharashtra", re.I | re.S), "Maharashtra"),
    (re.compile(r"stamp\s+paper.*?delhi",       re.I | re.S), "Delhi"),
    (re.compile(r"franking.*?maharashtra",      re.I | re.S), "Maharashtra"),
    (re.compile(r"e-?stamp.*?maharashtra",      re.I | re.S), "Maharashtra"),
    (re.compile(r"e-?stamp.*?karnataka",        re.I | re.S), "Karnataka"),
    (re.compile(r"e-?stamp.*?telangana",        re.I | re.S), "Telangana"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. SUB-REGISTRAR PATTERNS → STATE  (pre-compiled)
# ─────────────────────────────────────────────────────────────────────────────
_REGISTRAR_PATTERNS: list[tuple[re.Pattern, Optional[str]]] = [
    (re.compile(r"sub.?registrar.*?(mumbai|pune|nagpur|thane|nashik|aurangabad)",  re.I), "Maharashtra"),
    (re.compile(r"sub.?registrar.*?(bengaluru|bangalore|mysuru|mysore|hubli)",     re.I), "Karnataka"),
    (re.compile(r"sub.?registrar.*?(delhi|new delhi|south delhi|north delhi)",     re.I), "Delhi"),
    (re.compile(r"sub.?registrar.*?(chennai|madras|coimbatore|madurai)",           re.I), "Tamil Nadu"),
    (re.compile(r"sub.?registrar.*?(hyderabad|secunderabad|warangal)",             re.I), "Telangana"),
    (re.compile(r"sub.?registrar.*?(kolkata|calcutta|howrah)",                     re.I), "West Bengal"),
    (re.compile(r"sub.?registrar.*?(ahmedabad|surat|vadodara|rajkot)",             re.I), "Gujarat"),
    (re.compile(r"sub.?registrar.*?(lucknow|noida|agra|kanpur|varanasi)",          re.I), "Uttar Pradesh"),
    (re.compile(r"sub.?registrar.*?(dehradun|haridwar|roorkee|haldwani)",          re.I), "Uttarakhand"),
    (re.compile(r"sub.?registrar.*?(raipur|bilaspur|bhilai|durg)",                 re.I), "Chhattisgarh"),
    (re.compile(r"sub.?registrar.*?(bhopal|indore|jabalpur|gwalior)",              re.I), "Madhya Pradesh"),
    (re.compile(r"sub.?registrar.*?(patna|gaya|muzaffarpur)",                      re.I), "Bihar"),
    (re.compile(r"sub.?registrar.*?(ranchi|jamshedpur|dhanbad)",                   re.I), "Jharkhand"),
    (re.compile(r"sub.?registrar.*?(bhubaneswar|cuttack|rourkela)",                re.I), "Odisha"),
    (re.compile(r"sub.?registrar.*?(chandigarh|panchkula|mohali)",                 re.I), "Chandigarh"),
    # Generic fallback — extract the city and look it up
    (re.compile(r"registered\s+at.*?(mumbai|pune|bengaluru|bangalore|chennai|delhi|hyderabad)", re.I), None),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. JURISDICTION CLAUSE PATTERNS  (pre-compiled)
# ─────────────────────────────────────────────────────────────────────────────
_JURISDICTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"jurisdiction\s+of\s+courts?\s+(?:in|at|of)\s+([a-z\s]{3,40}?)[\.,\)]",  re.I),
    re.compile(r"subject\s+to\s+([a-z\s]{3,40}?)\s+jurisdiction",                         re.I),
    re.compile(r"courts?\s+(?:at|in|of)\s+([a-z\s]{3,40}?)\s+(?:shall|will|have|alone)",  re.I),
    re.compile(r"this\s+agreement\s+(?:is\s+)?(?:made|executed)\s+(?:at|in)\s+([a-z\s]{3,40}?)[\s,\.]", re.I),
    re.compile(r"exclusive\s+jurisdiction.*?(?:at|in|of)\s+([a-z\s]{3,40}?)[\.,\)]",      re.I),
]

# PIN code extractor
_PIN_RE = re.compile(r"\b([1-9][0-9]{5})\b")

# ─────────────────────────────────────────────────────────────────────────────
# 6. DOCUMENT TYPE CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────
DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "rental_agreement": [
        "monthly rent", "security deposit", "lessor", "lessee", "tenant",
        "landlord", "leave and license", "licensee", "licensor",
        "rental agreement", "lease agreement", "tenancy agreement",
        "lock-in period", "rent receipt", "premises", "demised premises",
    ],
    "employment_contract": [
        "designation", "ctc", "cost to company", "notice period",
        "employment bond", "employer", "employee", "joining date",
        "probation", "confirmation", "performance appraisal",
        "non-compete", "non-disclosure", "intellectual property",
        "termination", "resignation", "relieving letter",
    ],
    "loan_agreement": [
        "principal amount", "emi", "equated monthly", "interest rate",
        "collateral", "borrower", "lender", "repayment schedule",
        "foreclosure", "prepayment", "moratorium", "nbfc",
        "loan agreement", "credit agreement", "sanction letter",
    ],
    "legal_notice_eviction": [
        "vacate the premises", "quit and deliver", "termination of tenancy",
        "eviction notice", "evict", "vacant possession",
        "demand notice to vacate", "notice to quit",
    ],
    "legal_notice_recovery": [
        "outstanding dues", "recovery notice", "demand notice",
        "legal action", "pay forthwith", "outstanding amount",
        "debt recovery", "sarfaesi", "non-performing asset",
    ],
    "court_summons": [
        "you are hereby summoned", "appear before", "case no",
        "writ petition", "civil suit", "criminal case",
        "district court", "high court", "magistrate",
        "next date of hearing", "show cause",
    ],
    "vendor_contract": [
        "purchase order", "delivery schedule", "indemnity",
        "vendor", "supplier", "buyer", "goods", "services",
        "service level agreement", "sla", "penalty clause",
        "liquidated damages", "force majeure",
    ],
    "power_of_attorney": [
        "do hereby appoint", "attorney-in-fact", "act on my behalf",
        "power of attorney", "poa", "general power", "special power",
        "authorised to", "attorney to", "principal and agent",
    ],
    "gift_deed": [
        "transfer by way of gift", "donee", "without consideration",
        "gift deed", "donor", "gift of property",
        "out of love and affection", "natural love",
    ],
    "land_acquisition_notice": [
        "public purpose", "collector", "compensation",
        "land acquisition", "rfctlarr", "section 4", "section 6",
        "acquired by government", "compulsory acquisition",
    ],
    # ── NEW in v2 ─────────────────────────────────────────────────────────────
    "sale_deed": [
        "sale deed", "vendor", "vendee", "consideration amount",
        "sale consideration", "conveyance deed", "transfer of ownership",
        "absolute owner", "schedule of property", "market value",
        "stamp duty paid", "registered sale deed", "purchaser",
        "seller", "immovable property", "carpet area", "built-up area",
    ],
    "affidavit": [
        "i hereby solemnly affirm", "i hereby declare and state",
        "sworn before", "notary public", "deponent", "affirmation",
        "affidavit", "do solemnly swear", "to the best of my knowledge",
        "solemn affirmation", "oath", "depose and say",
    ],
    "mou": [
        "memorandum of understanding", "mou", "parties agree to",
        "letter of intent", "non-binding", "heads of agreement",
        "terms of collaboration", "in principle agreement",
        "good faith", "proposed transaction",
    ],
    "nda": [
        "non-disclosure agreement", "confidential information",
        "nda", "confidentiality agreement", "disclosing party",
        "receiving party", "proprietary information", "trade secret",
        "not to disclose", "shall keep confidential",
    ],
    "will_testament": [
        "last will and testament", "testator", "testatrix",
        "bequeath", "bequest", "executor", "executrix",
        "legatee", "residuary estate", "probate",
        "i hereby revoke", "testamentary capacity",
        "in the event of my death",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. LAW FRAMEWORK MATRIX  (state × doc_type → applicable laws)
# ─────────────────────────────────────────────────────────────────────────────
LAW_MATRIX: dict = {

    # ── RENTAL AGREEMENTS ────────────────────────────────────────────────────
    "rental_agreement": {
        "Maharashtra": {
            "central": [
                "Transfer of Property Act, 1882 (Sections 105–117)",
                "Indian Contract Act, 1872",
                "Registration Act, 1908 (Section 17 — mandatory for leases >1 year)",
            ],
            "state": ["Maharashtra Rent Control Act, 1999"],
            "key_rules": {
                "max_deposit":     "2 months rent (MRC Act Section 24)",
                "eviction_notice": "1 month minimum notice (MRC Act Section 16)",
                "rent_increase":   "Must be by written agreement (MRC Act Section 11)",
                "rent_court":      "Rent Court has jurisdiction, not Civil Court",
            },
        },
        "Delhi": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
                "Registration Act, 1908",
            ],
            "state": ["Delhi Rent Control Act, 1958"],
            "key_rules": {
                "max_deposit":     "No statutory cap (market standard: 2–3 months)",
                "eviction_notice": "15 days minimum (DRCA Section 14)",
                "standard_rent":   "Rent Controller can fix standard rent if disputed",
            },
        },
        "Karnataka": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
                "Registration Act, 1908",
            ],
            "state": ["Karnataka Rent Act, 2001"],
            "key_rules": {
                "max_deposit":     "No statutory cap (market standard: 10 months)",
                "eviction_notice": "1 month minimum (KRA Section 21)",
                "rent_court":      "Rent Controller has jurisdiction",
            },
        },
        "Tamil Nadu": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
                "Registration Act, 1908",
            ],
            "state": ["Tamil Nadu Buildings (Lease and Rent Control) Act, 1960"],
            "key_rules": {
                "max_deposit":     "3 months advance (TNBLRC Act Section 14)",
                "eviction_notice": "1 month (TNBLRC Act Section 10)",
            },
        },
        "Telangana": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["Telangana Premises (Regulation of Rent, Eviction) Act, 1949"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "1 month notice required",
            },
        },
        "West Bengal": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["West Bengal Premises Tenancy Act, 1997"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "As per agreement or 1 month",
            },
        },
        "Gujarat": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["Gujarat Rent Control Act, 1999"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "1 month (GRC Act)",
            },
        },
        "Uttar Pradesh": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["UP Urban Buildings (Regulation of Letting, Rent and Eviction) Act, 1972"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "As per UP Rent Act provisions",
            },
        },
        "Uttarakhand": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["Uttarakhand Urban Buildings (Regulation of Letting, Rent and Eviction) Act, 2011"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "1 month minimum",
            },
        },
        "Chhattisgarh": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": ["Chhattisgarh Accommodation Control Act, 1961"],
            "key_rules": {
                "max_deposit":     "No statutory cap",
                "eviction_notice": "1 month minimum",
            },
        },
        "DEFAULT": {
            "central": [
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
                "Registration Act, 1908",
            ],
            "state": [],
            "key_rules": {
                "note": "State-specific Rent Control Act applies — state could not be determined",
            },
        },
    },

    # ── EMPLOYMENT CONTRACTS ─────────────────────────────────────────────────
    "employment_contract": {
        "Maharashtra": {
            "central": [
                "Industrial Disputes Act, 1947",
                "Payment of Wages Act, 1936",
                "Minimum Wages Act, 1948",
                "Employees Provident Funds Act, 1952",
                "Employees State Insurance Act, 1948",
                "Payment of Gratuity Act, 1972",
                "Maternity Benefit Act, 1961",
                "POSH Act, 2013",
                "Indian Contract Act, 1872 (non-compete / bond clauses)",
            ],
            "state": ["Maharashtra Shops and Establishments Act, 2017"],
            "key_rules": {
                "notice_period": "Maharashtra SE Act — 30 days for employees >1 year",
                "bond_clause":   "Bond clauses enforceable only if reasonable (Contract Act Section 74)",
                "non_compete":   "Post-employment non-compete generally unenforceable (Contract Act Section 27)",
                "pf_deduction":  "Mandatory above Rs 15,000 basic salary",
                "gratuity":      "Payable after 5 years continuous service",
            },
        },
        "Karnataka": {
            "central": [
                "Industrial Disputes Act, 1947",
                "Payment of Wages Act, 1936",
                "Employees Provident Funds Act, 1952",
                "Payment of Gratuity Act, 1972",
                "Maternity Benefit Act, 1961",
                "POSH Act, 2013",
            ],
            "state": ["Karnataka Shops and Commercial Establishments Act, 1961"],
            "key_rules": {
                "notice_period": "Karnataka SE Act — varies by length of service",
                "non_compete":   "Post-employment non-compete generally unenforceable",
            },
        },
        "Delhi": {
            "central": [
                "Industrial Disputes Act, 1947",
                "Payment of Wages Act, 1936",
                "Employees Provident Funds Act, 1952",
                "Payment of Gratuity Act, 1972",
                "POSH Act, 2013",
            ],
            "state": ["Delhi Shops and Establishments Act, 1954"],
            "key_rules": {
                "notice_period": "Delhi SE Act — 30 days notice for employees >3 months",
            },
        },
        "DEFAULT": {
            "central": [
                "Industrial Disputes Act, 1947",
                "Payment of Wages Act, 1936",
                "Minimum Wages Act, 1948",
                "Employees Provident Funds Act, 1952",
                "Payment of Gratuity Act, 1972",
                "Maternity Benefit Act, 1961",
                "POSH Act, 2013",
                "Indian Contract Act, 1872",
            ],
            "state": [],
            "key_rules": {
                "note": "State Shops and Establishments Act applies — state could not be determined",
            },
        },
    },

    # ── LOAN AGREEMENTS ──────────────────────────────────────────────────────
    "loan_agreement": {
        "DEFAULT": {
            "central": [
                "Banking Regulation Act, 1949",
                "Reserve Bank of India Act, 1934",
                "SARFAESI Act, 2002",
                "Recovery of Debts and Bankruptcy Act, 1993",
                "Insolvency and Bankruptcy Code, 2016",
                "Consumer Protection Act, 2019",
                "Negotiable Instruments Act, 1881",
                "RBI Master Direction — Fair Practices Code for Lenders, 2023",
            ],
            "state": [],
            "key_rules": {
                "prepayment":      "RBI 2023 — no prepayment penalty for floating rate loans",
                "sarfaesi_notice": "Bank must give 60-day notice before taking possession",
                "penal_charges":   "RBI 2023 — penal charges must be reasonable, not compound",
                "grievance":       "Every bank must have a grievance redressal officer",
            },
        },
    },

    # ── LEGAL NOTICES ────────────────────────────────────────────────────────
    "legal_notice_eviction": {
        "DEFAULT": {
            "central": [
                "Transfer of Property Act, 1882",
                "Code of Civil Procedure, 1908 (Order 21)",
                "Specific Relief Act, 1963",
            ],
            "state": [],
            "key_rules": {
                "response_time": "You have the right to reply within the stated period",
                "legal_aid":     "Free legal aid if income < Rs 3 lakh (Legal Services Authorities Act 1987)",
            },
        },
    },
    "legal_notice_recovery": {
        "DEFAULT": {
            "central": [
                "SARFAESI Act, 2002",
                "Negotiable Instruments Act, 1881 (Section 138 — cheque bounce)",
                "Recovery of Debts Act, 1993",
                "Consumer Protection Act, 2019",
            ],
            "state": [],
            "key_rules": {
                "sarfaesi_cure": "60 days to repay after Section 13(2) notice",
                "drt_appeal":    "Appeal to DRT within 30 days of Section 13(4) notice",
                "ni_act_138":    "Reply to cheque bounce notice within 15 days",
            },
        },
    },
    "court_summons": {
        "DEFAULT": {
            "central": [
                "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
                "Bharatiya Nyaya Sanhita (BNS), 2023",
                "Code of Civil Procedure, 1908",
                "Bharatiya Sakshya Adhiniyam (BSA), 2023",
            ],
            "state": [],
            "key_rules": {
                "appearance":   "Must appear on hearing date — non-appearance risks ex-parte order",
                "legal_aid":    "Free legal aid if income < Rs 3 lakh",
                "written_stmt": "File written statement within 30 days in civil cases",
                "bnss_41a":     "Section 41A BNSS notice — appear before IO; arrest not immediate",
            },
        },
    },

    # ── OTHER DOCUMENT TYPES ─────────────────────────────────────────────────
    "vendor_contract": {
        "DEFAULT": {
            "central": [
                "Indian Contract Act, 1872",
                "Sale of Goods Act, 1930",
                "MSME Development Act, 2006 (45-day payment rule for MSMEs)",
                "Arbitration and Conciliation Act, 1996",
                "GST Act, 2017 (for tax clauses)",
            ],
            "state": [],
            "key_rules": {
                "msme_payment": "If you are an MSME, buyer must pay within 45 days",
                "arbitration":  "Arbitration clause is binding — check venue before signing",
            },
        },
    },
    "power_of_attorney": {
        "DEFAULT": {
            "central": [
                "Powers of Attorney Act, 1882",
                "Registration Act, 1908",
                "Transfer of Property Act, 1882",
                "Indian Contract Act, 1872",
            ],
            "state": [],
            "key_rules": {
                "registration":   "POA for immovable property must be registered",
                "revocation":     "Principal can revoke POA at any time",
                "senior_warning": "General POA gives extremely wide powers — be careful",
            },
        },
    },
    "gift_deed": {
        "DEFAULT": {
            "central": [
                "Transfer of Property Act, 1882 (Sections 122–129)",
                "Registration Act, 1908 (mandatory for immovable property gifts)",
                "Income Tax Act, 1961 (gift tax implications)",
                "Hindu Succession Act, 1956",
            ],
            "state": [],
            "key_rules": {
                "registration": "Gift of immovable property is void without registration",
                "revocation":   "Gift cannot be revoked once accepted",
                "stamp_duty":   "Stamp duty applies — varies by state",
            },
        },
    },
    "land_acquisition_notice": {
        "DEFAULT": {
            "central": [
                "RFCTLARR Act, 2013",
                "National Highways Act, 1956 (for highway projects)",
            ],
            "state": [],
            "key_rules": {
                "compensation": "2x market value for rural land, 1x for urban + solatium",
                "consent":      "80% consent required for PPP projects",
                "r_and_r":      "You are entitled to Rehabilitation & Resettlement benefits",
            },
        },
    },

    # ── NEW DOC TYPES IN v2 ───────────────────────────────────────────────────
    "sale_deed": {
        "Maharashtra": {
            "central": [
                "Transfer of Property Act, 1882 (Section 54)",
                "Registration Act, 1908 (mandatory)",
                "Indian Contract Act, 1872",
                "Income Tax Act, 1961 (TDS on property > Rs 50 lakh)",
            ],
            "state": [
                "Maharashtra Stamp Act, 1958",
                "Maharashtra Land Revenue Code, 1966",
            ],
            "key_rules": {
                "registration":     "Registration is mandatory — unregistered sale deed is void",
                "stamp_duty":       "Maharashtra: 5% of property value (3% for women buyers)",
                "tds":              "Buyer must deduct 1% TDS if sale > Rs 50 lakh",
                "rera":             "Check RERA registration if buying from developer",
                "encumbrance":      "Obtain EC from sub-registrar before purchase",
            },
        },
        "Karnataka": {
            "central": [
                "Transfer of Property Act, 1882 (Section 54)",
                "Registration Act, 1908",
                "Income Tax Act, 1961",
            ],
            "state": [
                "Karnataka Stamp Act, 1957",
                "Karnataka Land Revenue Act, 1964",
            ],
            "key_rules": {
                "registration": "Mandatory within 4 months of execution",
                "stamp_duty":   "Karnataka: 5.6% of property value",
                "khata":        "Transfer of Khata from seller to buyer required",
            },
        },
        "DEFAULT": {
            "central": [
                "Transfer of Property Act, 1882 (Section 54)",
                "Registration Act, 1908 (mandatory)",
                "Indian Contract Act, 1872",
                "Income Tax Act, 1961 (TDS on property > Rs 50 lakh)",
                "RERA Act, 2016 (if buying from developer)",
            ],
            "state": [],
            "key_rules": {
                "registration": "Registration is mandatory — unregistered sale deed is void",
                "tds":          "Buyer must deduct 1% TDS if sale > Rs 50 lakh",
                "encumbrance":  "Obtain EC from sub-registrar before purchase",
                "rera":         "Check RERA registration if buying from developer",
            },
        },
    },
    "affidavit": {
        "DEFAULT": {
            "central": [
                "Indian Evidence Act, 1872 / Bharatiya Sakshya Adhiniyam, 2023",
                "Code of Civil Procedure, 1908 (Order XIX)",
                "Oaths Act, 1969",
                "Notaries Act, 1952",
            ],
            "state": [],
            "key_rules": {
                "execution":    "Must be sworn before a Magistrate, Notary, or Oath Commissioner",
                "false_oath":   "False affidavit is punishable under BNS Section 224 (perjury)",
                "stamp_duty":   "Nominal stamp duty applicable (varies by state)",
                "verification": "Self-attested affidavit is not valid for court proceedings",
            },
        },
    },
    "mou": {
        "DEFAULT": {
            "central": [
                "Indian Contract Act, 1872",
                "Specific Relief Act, 1963",
                "Arbitration and Conciliation Act, 1996",
            ],
            "state": [],
            "key_rules": {
                "enforceability":  "An MoU is enforceable if it satisfies Contract Act essentials",
                "non_binding":     "MoU can be made non-binding — ensure this is explicitly stated",
                "intention":       "Courts look at intention to create legal relations",
                "arbitration":     "Include arbitration clause to avoid court disputes",
            },
        },
    },
    "nda": {
        "DEFAULT": {
            "central": [
                "Indian Contract Act, 1872",
                "Information Technology Act, 2000",
                "Indian Penal Code / Bharatiya Nyaya Sanhita, 2023",
                "Arbitration and Conciliation Act, 1996",
            ],
            "state": [],
            "key_rules": {
                "scope":        "Define 'confidential information' narrowly and specifically",
                "duration":     "Perpetual NDAs may be challenged — 3–5 years is standard",
                "remedies":     "Specify injunctive relief as a remedy in addition to damages",
                "trade_secret": "No specific trade secret law in India — rely on Contract Act",
                "non_compete":  "Post-employment non-compete clauses in NDA are generally unenforceable",
            },
        },
    },
    "will_testament": {
        "DEFAULT": {
            "central": [
                "Indian Succession Act, 1925",
                "Hindu Succession Act, 1956 (for Hindus, Sikhs, Jains, Buddhists)",
                "Muslim Personal Law (Shariat) Application Act, 1937",
                "Registration Act, 1908 (registration optional but recommended)",
            ],
            "state": [],
            "key_rules": {
                "registration":  "Registration of Will is optional but highly recommended",
                "witnesses":     "Will must be signed by testator and attested by 2 witnesses",
                "probate":       "Probate mandatory in Mumbai, Chennai, Kolkata — not elsewhere",
                "revocation":    "Will is revocable at any time during lifetime",
                "muslim_limit":  "Muslims can bequest only up to 1/3rd of estate without heir consent",
            },
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 8. PRIVATE HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pins(text: str) -> list[str]:
    """Extract all 6-digit Indian PIN codes from text."""
    return _PIN_RE.findall(text)


def _pin_to_state(pin: str) -> Optional[str]:
    """Map a PIN code to its state using the first 2 digits."""
    return PIN_PREFIX_TO_STATE.get(pin[:2])


def _extract_cities(text: str, limit_chars: Optional[int] = None) -> list[tuple[str, str]]:
    """
    Find city/district names in text using the gazetteer.
    Uses the pre-sorted _SORTED_CITIES list — no sorting overhead per call.
    limit_chars: if set, only searches in text[:limit_chars]
    """
    search_text = (text[:limit_chars] if limit_chars else text).lower()
    found: list[tuple[str, str]] = []
    seen_states: set[str] = set()
    for city, state in _SORTED_CITIES:
        if city in search_text:
            found.append((city, state))
            seen_states.add(state)
    return found


def _check_stamp_paper(text: str) -> Optional[tuple[str, float]]:
    """Detect state from stamp paper mentions. Returns (state, confidence) or None."""
    for pattern, state in _STAMP_PATTERNS:
        if pattern.search(text):
            return state, 0.98
    return None


def _check_registrar(text: str) -> Optional[tuple[str, float]]:
    """Detect state from Sub-Registrar mentions. Returns (state, confidence) or None."""
    for pattern, state in _REGISTRAR_PATTERNS:
        match = pattern.search(text)
        if match:
            if state:
                return state, 0.95
            # Generic fallback — extract city and look it up
            city_found = match.group(1).strip().lower()
            st = CITY_TO_STATE.get(city_found)
            if st:
                return st, 0.93
    return None


def _check_jurisdiction_clause(text: str) -> Optional[tuple[str, str, float]]:
    """
    Extract state from an explicit jurisdiction clause.
    Returns (state, matched_location_text, confidence) or None.
    """
    text_lower = text.lower()
    for pattern in _JURISDICTION_PATTERNS:
        match = pattern.search(text_lower)
        if match:
            extracted = match.group(1).strip()
            # Try city map first
            st = CITY_TO_STATE.get(extracted)
            if st:
                return st, extracted, 0.90
            # Try substring state name match
            for state_name in set(CITY_TO_STATE.values()):
                if state_name.lower() in extracted:
                    return state_name, extracted, 0.90
    return None


def classify_document_type(text: str) -> tuple[str, float]:
    """
    Classify the document type using keyword matching.
    Returns (doc_type, confidence_score).
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        scores[doc_type] = hits

    if not scores:
        return "unknown", 0.0

    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    raw_hits = scores[best_type]

    if raw_hits < 2:
        return "unknown", 0.0

    confidence = min(0.95, 0.50 + (raw_hits * 0.07))
    return best_type, round(confidence, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 9. MAIN PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def detect_jurisdiction(text: str) -> dict:
    """
    Main ALJI function. Analyses document text and returns full jurisdiction info.

    Returns a dict with:
        state           — detected Indian state (or None)
        confidence      — 0.0 to 1.0 (boosted if multiple signals agree)
        signal_used     — primary detection signal
        signals_found   — list of all signals detected (for transparency)
        doc_type        — document type classification
        doc_type_conf   — document type confidence
        laws            — dict with 'central', 'state', 'key_rules'
        conflict        — dict if jurisdiction conflict detected, else None
        transparency    — human-readable explanation of what was detected
    """
    result: dict = {
        "state":          None,
        "confidence":     0.0,
        "signal_used":    None,
        "signals_found":  [],
        "doc_type":       "unknown",
        "doc_type_conf":  0.0,
        "laws":           {},
        "conflict":       None,
        "transparency":   "",
    }

    # ── Classify document type ────────────────────────────────────────────────
    doc_type, doc_conf = classify_document_type(text)
    result["doc_type"]      = doc_type
    result["doc_type_conf"] = doc_conf

    # ── Collect ALL signals first ─────────────────────────────────────────────
    # We gather every signal that fires, then pick the winner and check consensus.
    all_signals: list[dict] = []

    # Signal 1: Stamp paper (most reliable)
    stamp = _check_stamp_paper(text)
    if stamp:
        all_signals.append({"source": "stamp_paper", "state": stamp[0], "confidence": stamp[1]})

    # Signal 2: Sub-Registrar office
    reg = _check_registrar(text)
    if reg:
        all_signals.append({"source": "registrar_office", "state": reg[0], "confidence": reg[1]})

    # Signal 3: PIN codes (full document)
    pins = _extract_pins(text)
    seen_pin_states: set[str] = set()
    for pin in pins:
        st = _pin_to_state(pin)
        if st and st not in seen_pin_states:
            seen_pin_states.add(st)
            all_signals.append({"source": f"pin_code_{pin}", "state": st, "confidence": 0.93})

    # Signal 4: Jurisdiction clause
    jc = _check_jurisdiction_clause(text)
    jc_state: Optional[str] = None
    jc_location: Optional[str] = None
    if jc:
        jc_state, jc_location, jc_conf = jc
        all_signals.append({"source": "jurisdiction_clause", "state": jc_state, "confidence": jc_conf})

    # Signal 5: City names in document header (first 2000 chars)
    header_cities = _extract_cities(text, limit_chars=2000)
    for city_name, city_state in header_cities[:3]:
        all_signals.append({"source": f"city_name_{city_name}", "state": city_state, "confidence": 0.75})

    result["signals_found"] = all_signals

    if not all_signals:
        result["transparency"] = (
            "No location signals found in this document. "
            "Analysis uses central Indian law only. "
            "For more accurate results, please mention your city or state."
        )
        _load_laws(result, doc_type, None)
        return result

    # ── Winner selection: highest confidence signal ───────────────────────────
    best = max(all_signals, key=lambda s: s["confidence"])
    detected_state: str = best["state"]
    confidence: float   = best["confidence"]
    signal: str         = best["source"]

    # ── Consensus bonus: if multiple independent sources agree, boost confidence
    agreeing = [
        s for s in all_signals
        if s["state"] == detected_state and s["source"] != signal
    ]
    if agreeing:
        # +0.03 per additional agreeing signal, capped at 0.99
        bonus = min(0.03 * len(agreeing), 0.06)
        confidence = min(0.99, confidence + bonus)

    result["state"]       = detected_state
    result["confidence"]  = round(confidence, 2)
    result["signal_used"] = signal

    # ── Conflict detection ────────────────────────────────────────────────────
    conflicts: list[dict] = []

    # Conflict type A: jurisdiction clause vs address/PIN/stamp
    if jc_state and jc_state != detected_state and signal != "jurisdiction_clause":
        conflicts.append({
            "type":    "clause_vs_address",
            "detail":  (
                f"Jurisdiction clause names {jc_state} courts "
                f"but the document address/stamp paper indicates {detected_state}."
            ),
        })

    # Conflict type B: multiple PIN codes pointing to different states
    if len(seen_pin_states) > 1:
        conflicts.append({
            "type":   "multiple_pin_states",
            "detail": f"PIN codes in document suggest multiple states: {', '.join(sorted(seen_pin_states))}.",
        })

    # Conflict type C: city signals disagree with winning signal
    city_states = {s["state"] for s in all_signals if s["source"].startswith("city_name_")}
    if city_states and detected_state not in city_states and not city_states.issubset({jc_state}):
        conflicts.append({
            "type":   "city_vs_winner",
            "detail": f"City names in document suggest {', '.join(sorted(city_states))} but primary signal indicates {detected_state}.",
        })

    if conflicts:
        result["conflict"] = {
            "conflicts": conflicts,
            "governing_state": detected_state,
            "message": (
                f"⚠️ Jurisdiction signal conflict detected. "
                f"NyayaSetu has analysed this document under {detected_state} law "
                f"(based on '{signal.replace('_', ' ')}', the most reliable signal found). "
                + " | ".join(c["detail"] for c in conflicts)
                + " If this is incorrect, you can manually specify your state."
            ),
        }

    # ── Load law framework ────────────────────────────────────────────────────
    _load_laws(result, doc_type, detected_state)

    # ── Transparency message ──────────────────────────────────────────────────
    doc_label = doc_type.replace("_", " ").title()
    law_preview = ", ".join(result["laws"].get("central", [])[:2])
    state_law   = result["laws"].get("state", [])

    if confidence >= 0.75:
        result["transparency"] = (
            f"This appears to be a {doc_label} governed by {detected_state} law "
            f"(confidence: {int(confidence * 100)}%, detected via: {signal.replace('_', ' ')}). "
            f"Analysis is based on: {law_preview}"
            + (f" + {state_law[0]}" if state_law else "")
            + "."
        )
        if agreeing:
            result["transparency"] += (
                f" ({len(agreeing)} additional signal(s) confirmed the same state.)"
            )
    elif confidence >= 0.50:
        result["transparency"] = (
            f"We believe this is a {doc_label} governed by {detected_state} law "
            f"(confidence: {int(confidence * 100)}%). "
            "If this is incorrect, manually specify your state for more accurate results."
        )
    else:
        result["transparency"] = (
            f"Could not determine the governing state from this document. "
            "Analysis uses central Indian law only. "
            "Please mention your city or state for more accurate results."
        )

    return result


def _load_laws(result: dict, doc_type: str, state: Optional[str]) -> None:
    """Internal helper: populate result['laws'] from LAW_MATRIX."""
    if doc_type == "unknown":
        return
    doc_laws = LAW_MATRIX.get(doc_type, {})
    if state:
        result["laws"] = doc_laws.get(state) or doc_laws.get("DEFAULT", {})
    else:
        result["laws"] = doc_laws.get("DEFAULT", {})


def get_law_framework(state: str, doc_type: str) -> dict:
    """
    Directly fetch the law framework for a given state + document type.
    Useful when state is already known (e.g., user selected it manually).
    """
    doc_laws = LAW_MATRIX.get(doc_type, {})
    return doc_laws.get(state) or doc_laws.get("DEFAULT", {})


def get_rag_context(jurisdiction_result: dict) -> str:
    """
    Converts ALJI output into a context string to prepend to LLM prompts.
    Inject this into your RAG calls before the user's question.

    Usage in document_analyzer.py:
        from alji import detect_jurisdiction, get_rag_context
        j   = detect_jurisdiction(doc_text)
        ctx = get_rag_context(j)
        prompt = ctx + "\\n\\n" + user_question
    """
    if not jurisdiction_result.get("laws"):
        return ""

    laws     = jurisdiction_result["laws"]
    state    = jurisdiction_result.get("state", "India")
    doc_type = jurisdiction_result.get("doc_type", "document")
    conflict = jurisdiction_result.get("conflict")

    lines = [
        "[JURISDICTION CONTEXT]",
        f"Document type : {doc_type.replace('_', ' ').title()}",
        f"Governing law : {state}",
        f"Confidence    : {int(jurisdiction_result.get('confidence', 0) * 100)}%",
        f"Signal        : {jurisdiction_result.get('signal_used', 'unknown')}",
        "",
        "Applicable Central Laws:",
    ]
    for law in laws.get("central", []):
        lines.append(f"  - {law}")

    if laws.get("state"):
        lines.append("")
        lines.append("Applicable State Laws:")
        for law in laws["state"]:
            lines.append(f"  - {law}")

    if laws.get("key_rules"):
        lines.append("")
        lines.append("Key Legal Rules:")
        for rule_name, rule_text in laws["key_rules"].items():
            lines.append(f"  - {rule_name.replace('_', ' ').title()}: {rule_text}")

    if conflict:
        lines.append("")
        lines.append(f"⚠️  CONFLICT NOTE: {conflict['message']}")

    lines += ["[END JURISDICTION CONTEXT]", ""]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 10. SELF-TEST  — run directly to verify: python alji.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_docs = [
        {
            "name": "Maharashtra Rental Agreement (stamp paper signal)",
            "text": """
                LEAVE AND LICENSE AGREEMENT
                This agreement is made at Mumbai on 1 January 2024.
                Maharashtra Stamp Paper Rs. 500.
                Licensor: Flat 4B, Andheri West, Mumbai 400053.
                Monthly rent: Rs. 25,000. Security deposit: Rs. 1,50,000.
                The Licensor may terminate this agreement without prior notice.
                Subject to jurisdiction of courts in Mumbai.
            """,
        },
        {
            "name": "Delhi Employment Contract",
            "text": """
                EMPLOYMENT AGREEMENT executed at New Delhi on 15 March 2024.
                Employee appointed as Software Engineer. CTC: Rs. 12,00,000 p.a.
                Notice period: 90 days. Non-compete: 2 years post-employment.
                Employment bond: Rs. 2,00,000 if leaving within 1 year.
                Jurisdiction: Delhi courts.
            """,
        },
        {
            "name": "Conflict Case — Delhi courts but Noida address",
            "text": """
                RENTAL AGREEMENT
                Property: Flat 7C, Sector 62, Noida, Uttar Pradesh 201309.
                Monthly rent Rs. 18,000. Security deposit Rs. 1,08,000.
                Subject to exclusive jurisdiction of Delhi courts.
            """,
        },
        {
            "name": "Chhattisgarh Sale Deed (v2 new state)",
            "text": """
                SALE DEED
                Executed at Raipur, Chhattisgarh on 10 February 2024.
                PIN code 492001. Sale consideration Rs. 45,00,000.
                The Vendor hereby transfers absolute ownership of the said
                immovable property to the Vendee. Stamp duty paid as per
                Chhattisgarh Stamp Act. Registered at Sub-Registrar Raipur.
            """,
        },
        {
            "name": "NDA — no location info",
            "text": """
                NON-DISCLOSURE AGREEMENT
                Between Disclosing Party and Receiving Party.
                All confidential information, trade secrets, and proprietary
                information shared shall not to disclose to any third party.
                Duration: 3 years from execution date.
            """,
        },
        {
            "name": "Will and Testament",
            "text": """
                LAST WILL AND TESTAMENT
                I, the testator, being of sound mind, do hereby revoke all
                previous Wills. I bequeath my entire residuary estate to my
                daughter. My executor is appointed to carry out these wishes.
                Signed in presence of 2 witnesses.
            """,
        },
    ]

    print("=" * 65)
    print("ALJI v2.0 — Automatic Legal Jurisdiction Identification")
    print("NyayaSetu Self-Test")
    print("=" * 65)

    for doc in test_docs:
        print(f"\n📄 {doc['name']}")
        print("-" * 50)
        r = detect_jurisdiction(doc["text"])
        print(f"  State        : {r['state']}")
        print(f"  Confidence   : {r['confidence']}")
        print(f"  Signal       : {r['signal_used']}")
        print(f"  Doc Type     : {r['doc_type']} ({r['doc_type_conf']})")
        print(f"  Transparency : {r['transparency'][:110]}...")
        if r["conflict"]:
            print(f"  ⚠️  CONFLICT  : {r['conflict']['message'][:110]}...")
        print(f"\n  RAG Context (first 8 lines):")
        for line in get_rag_context(r).split("\n")[:8]:
            print(f"    {line}")