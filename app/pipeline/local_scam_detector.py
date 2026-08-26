import re

SCAM_KEYWORDS = {
    "urgency": [
        "act now", "immediately", "right now", "urgent", "urgently",
        "last warning", "final notice", "within 24 hours", "within an hour",
        "account will be blocked", "account will be suspended", "account will be closed",
        "expires today", "limited time", "before it's too late", "don't delay",
        "abhi turant", "jaldi karo", "abhi karna hoga", "turant karo"
    ],
    "otp_credential": [
        "otp", "one time password", "verification code", "security code",
        "cvv", "cvv number", "share the code", "share the otp", "tell me the otp",
        "pin number", "atm pin", "card pin", "password", "login details",
        "net banking password", "mpin", "upi pin", "aadhaar number", "aadhar number",
        "pan number", "pan card details", "otp bhejo", "otp batao", "code batao"
    ],
    "payment_request": [
        "upi", "upi id", "google pay", "phonepe", "paytm", "bank transfer",
        "wire transfer", "wire the money", "gift card", "gift card code",
        "processing fee", "refundable deposit", "advance payment", "security deposit",
        "customs fee", "clearance fee", "unlock fee", "penalty amount",
        "pay immediately", "make the payment", "transfer the amount",
        "paisa bhejo", "payment karo", "advance fee"
    ],
    "impersonation": [
        "rbi", "reserve bank of india", "income tax department", "income tax officer",
        "customs department", "customs officer", "cyber cell", "cyber crime",
        "police station", "police officer", "cbi", "enforcement directorate",
        "courier company", "fedex", "dhl", "bluedart", "trai", "sim card department",
        "electricity board", "power department", "bank manager", "bank official",
        "amazon support", "microsoft support", "tech support", "government official"
    ],
    "emotional_manipulation": [
        "arrest warrant", "legal action", "case filed against you", "fir filed",
        "your account is compromised", "your account is hacked", "suspicious activity",
        "family member in trouble", "accident", "hospital emergency", "emergency situation",
        "jail", "court notice", "summons", "you will be arrested",
        "giriftar", "case darj", "warrant jaari"
    ],
    "isolation_secrecy": [
        "don't tell anyone", "keep this confidential", "don't hang up",
        "don't disconnect the call", "stay on the line", "don't tell your family",
        "don't tell your bank", "this is between us", "keep it private",
        "kisi ko mat batana", "phone mat kato", "line par raho"
    ],
    "prize_lottery_scam": [
        "you have won", "lottery", "lucky draw", "prize money", "cash prize",
        "congratulations you have won", "claim your prize", "winner selected",
        "kbc lottery", "lucky winner"
    ],
    "job_investment_scam": [
        "work from home", "guaranteed returns", "double your money", "investment opportunity",
        "part time job", "easy money", "quick money", "high returns guaranteed",
        "crypto investment", "trading account", "binary trading"
    ],
    "remote_access": [
        "anydesk", "teamviewer", "remote access", "install this app", "screen share",
        "quick support", "download this application", "give me access to your screen"
    ]
}

CATEGORY_WEIGHTS = {
    "otp_credential": 3.0,
    "payment_request": 3.0,
    "remote_access": 3.0,
    "impersonation": 2.0,
    "emotional_manipulation": 2.0,
    "isolation_secrecy": 2.0,
    "prize_lottery_scam": 1.5,
    "job_investment_scam": 1.5,
    "urgency": 1.0,
}


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching - lowercase, remove punctuation, normalize whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_transcript(transcript: str):
    """
    Returns (risk_score: float, matched_flags: dict, evidence_list: list[str])
    Fully offline — no external API calls.
    """
    text = normalize_text(transcript)
    matched_categories = {}
    evidence = []

    for category, phrases in SCAM_KEYWORDS.items():
        found = [p for p in phrases if p in text]
        if found:
            matched_categories[category] = found

    risk_score = sum(
        CATEGORY_WEIGHTS.get(cat, 1.0) for cat in matched_categories
    )

    # Require at least 2 distinct category hits before treating as meaningful
    # signal, to reduce false positives from a single generic word.
    if len(matched_categories) < 2:
        risk_score *= 0.5

    for category, phrases in matched_categories.items():
        readable_category = category.replace("_", " ").title()
        evidence.append(f"{readable_category} language detected: {', '.join(phrases)}")

    return risk_score, matched_categories, evidence