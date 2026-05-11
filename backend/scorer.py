import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

NOVACODE_PROFILE = """
NovaCode Consulting (Pty) Ltd is a Cape Town & Pretoria-based AI, automation, and software consultancy.

CORE PRODUCTS:
- NovaBanks: Real-time bank statement analytics engine — fraud detection, income verification, behavioural profiling. Does NOT store statements (strong privacy position).
- NovaCollect: Debtors management and collections automation platform.
- NovaLoans: End-to-end loan origination with facial recognition onboarding, AI decisioning (Gradient Boosted Trees), React/Python FastAPI/PostgreSQL stack.

CAPABILITIES:
- AI/ML: Fraud detection, credit scoring, machine learning, NLP, predictive analytics
- Software development: Python, React, FastAPI, PostgreSQL, REST APIs
- Fintech: Lending platforms, payment reconciliation, DDACC, bank statement analysis
- Automation: Business process automation, middleware, reconciliation systems
- Data: Analytics pipelines, BI dashboards, data engineering
- Consulting: Digital transformation, ICT strategy, financial sector consulting
- Compliance: NCR credit provider experience, POPIA, financial sector regulation

TARGET SECTORS: Financial services (primary), government, insurance, telecommunications, healthcare

TRACK RECORD: NCR registered credit provider operations, document automation systems, bank reconciliation middleware, AI-powered lending decisions, compliance automation.

TEAM SIZE: Small but capable — 2 directors (AI/tech + operations), with associate network. Best suited for R500K–R15M contracts.
"""


async def score_tender(tender: dict) -> tuple[int, str]:
    """Score a tender 0-100 for NovaCode relevance using Claude."""
    if not ANTHROPIC_API_KEY:
        return _rule_based_score(tender)

    prompt = f"""You are evaluating a government tender for relevance to NovaCode Consulting.

NOVACODE PROFILE:
{NOVACODE_PROFILE}

TENDER TO EVALUATE:
Title: {tender.get('title', '')}
Department: {tender.get('department', '')}
Category: {tender.get('category', '')}
Country: {tender.get('country', '')}
Value: {tender.get('value_raw', 'Unknown')}
Description: {tender.get('description', 'Not provided')[:500]}

Score this tender from 0 to 100 for NovaCode's relevance and win potential.
- 80-100: Excellent fit, NovaCode should prioritise and bid aggressively
- 60-79: Good fit, worth a strong proposal
- 40-59: Moderate fit, consider if bandwidth allows
- 20-39: Low fit, minor overlap only
- 0-19: Not relevant, do not pursue

Respond ONLY with valid JSON, no other text:
{{"score": <integer 0-100>, "reason": "<2-3 sentence explanation of the score and key bid considerations>"}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = response.json()
            text = data["content"][0]["text"].strip()
            parsed = json.loads(text)
            score = max(0, min(100, int(parsed["score"])))
            reason = parsed.get("reason", "")
            return score, reason
    except Exception as e:
        logger.warning(f"Claude scoring failed, using rule-based fallback: {e}")
        return _rule_based_score(tender)


def _rule_based_score(tender: dict) -> tuple[int, str]:
    """Fallback scoring when Claude API is unavailable."""
    title = (tender.get("title") or "").lower()
    desc = (tender.get("description") or "").lower()
    cat = (tender.get("category") or "").lower()
    combined = f"{title} {desc} {cat}"

    score = 0
    matched = []

    high_value = [
        ("artificial intelligence", 25), ("machine learning", 22), ("ai ", 20),
        ("fraud detection", 22), ("loan origination", 22), ("credit scoring", 20),
        ("fintech", 18), ("bank statement", 20), ("payment reconciliation", 18),
    ]
    mid_value = [
        ("digital transformation", 14), ("automation", 14), ("data analytics", 14),
        ("software development", 12), ("ict consulting", 14), ("business intelligence", 12),
        ("api", 8), ("python", 10), ("react", 10), ("fastapi", 12),
    ]
    low_value = [
        ("consulting", 6), ("ict", 8), ("technology", 6), ("digital", 6),
        ("system", 5), ("platform", 5), ("data", 5),
    ]

    for kw, pts in high_value:
        if kw in combined:
            score += pts
            matched.append(kw)

    for kw, pts in mid_value:
        if kw in combined and kw not in matched:
            score += pts
            matched.append(kw)

    for kw, pts in low_value:
        if kw in combined and kw not in matched:
            score += pts

    score = min(100, score)
    reason = f"Rule-based score. Matched keywords: {', '.join(matched[:4]) if matched else 'none'}."
    return score, reason
