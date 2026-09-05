"""Security screening for agent inputs — prompt injection detection and PII scanning."""
import re
import time

# Simple pattern-based prompt injection detection
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
    r"you\s+are\s+now\s+(a|an|the)\s+",
    r"disregard\s+(your|all|any)\s+(instructions|rules|guidelines)",
    r"pretend\s+(you|to)\s+(are|be)",
    r"system\s*prompt",
    r"\]\]>.*<",
    r"<script",
    r"act\s+as\s+(if|a|an)",
    r"jailbreak",
    r"DAN\s+mode",
]

# PII patterns for detection
PII_PATTERNS = {
    "US_SOCIAL_SECURITY_NUMBER": r"\b\d{3}-\d{2}-\d{4}\b",
    "CREDIT_CARD_NUMBER": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
    "EMAIL_ADDRESS": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE_NUMBER": r"\b(?:\+1[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b",
    "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}


def scan_prompt_injection(text: str) -> dict:
    """Check for prompt injection patterns."""
    text_lower = text.lower()
    detections = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            detections.append(pattern)
    return {
        "is_injection": len(detections) > 0,
        "confidence": min(1.0, len(detections) * 0.4),
        "patterns_matched": len(detections),
    }


def scan_pii(text: str) -> dict:
    """Detect and optionally redact PII from text."""
    findings = []
    redacted_text = text
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            findings.append({"type": pii_type, "count": len(matches)})
            redacted_text = re.sub(pattern, f"[{pii_type}]", redacted_text)
    return {
        "has_pii": len(findings) > 0,
        "findings": findings,
        "total_redactions": sum(f["count"] for f in findings),
        "redacted_text": redacted_text,
    }


def screen_input(text: str) -> dict:
    """Full security screening of input text."""
    injection = scan_prompt_injection(text)
    pii = scan_pii(text)
    return {
        "safe": not injection["is_injection"],
        "injection": injection,
        "pii": pii,
        "screened_text": pii["redacted_text"] if pii["has_pii"] else text,
    }
