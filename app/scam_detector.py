"""
ScamDetector — Automated Risk Assessment Engine for Internship Postings
=======================================================================

PURPOSE
-------
Evaluates internship postings using weighted rule-based and pattern-based
heuristics to surface likely scams before they reach students. The detector
assigns a numeric risk score (0–100) and a risk level (Low / Medium / High),
and lists every rule that fired along with a human-readable explanation.

WHAT THIS MODULE DOES NOT DO
-----------------------------
- It does NOT visit, fetch, or follow any URL found in posting text.
- It does NOT guarantee that a flagged posting is fraudulent; it produces
  probabilistic signals only.
- It does NOT access any external data source, network endpoint, or database
  directly. Duplicate detection requires callers to supply comparison texts.

DECISIONS REQUIRING HUMAN REVIEW
---------------------------------
Any posting whose final risk_level is 'High' (score >= 61) is automatically
flagged with requires_human_review=True and must be queued for administrator
inspection before it is shown to students.

LIMITATIONS
-----------
- Rule-based only: sophisticated scam text that avoids known keywords will
  not be caught.
- May produce false positives — legitimate postings may occasionally trigger
  one or more rules, especially the vague-content or urgency checks.
- Duplicate detection uses word-bigram Jaccard similarity; near-duplicate
  paraphrases with significantly different wording may be missed.
- Stipend thresholds are hard-coded; adjust RULES_CONFIG for different
  currency contexts.
"""

import re
from urllib.parse import urlparse


class ScamDetector:
    """
    Automated Scam Detection Engine for Internship Postings.

    Evaluates postings using weighted rule-based and pattern-based heuristics.
    All public behaviour is accessed through the class methods
    ``evaluate_posting`` and ``check_duplicate``; no instance is required.
    """

    # ------------------------------------------------------------------
    # Configuration — all thresholds and weights in one place
    # ------------------------------------------------------------------
    RULES_CONFIG = {
        'thresholds': {
            'low_max':    30,   # score  0–30  → Low
            'medium_max': 60,   # score 31–60  → Medium; >= 61 → High
        },
        'weights': {
            'payment_demand':       35,  # Critical
            'credential_request':   35,  # Critical
            'unrealistic_offer':    25,
            'suspicious_link':      20,
            'contact_safety':       20,
            'urgency_pressure':     15,
            'vague_content':        15,
            'spam_repetition':      20,  # NEW
            'duplicate_similarity': 30,  # NEW (only when existing_descriptions provided)
            'instructions_risk':    20,  # NEW
        },
    }

    # ------------------------------------------------------------------
    # 1. Upfront Payment & Financial Demands  (Critical weight)
    # ------------------------------------------------------------------
    PAYMENT_PATTERNS = [
        r'\bregistration fee\b',
        r'\bsecurity deposit\b',
        r'\btraining fee\b',
        r'\bpay to confirm\b',
        r'\brefundable amount\b',
        r'\bprocessing fee\b',
        r'\blaptop deposit\b',
        r'\bdocument charges\b',
        r'\bapplication fee\b',
        r'\bpayable amount\b',
        r'\bpay before joining\b',
        r'\bbuy software kit\b',
        r'\bpay\s*(?:rs\.?|inr|₹|\$)\s*\d+',
        r'\binvestment required\b',
        r'\bpaid training mandatory\b',
    ]

    # ------------------------------------------------------------------
    # 2. Credential / Sensitive-Data Requests  (Critical weight) — NEW
    # ------------------------------------------------------------------
    CREDENTIAL_PATTERNS = [
        r'\bshare your otp\b',
        r'\bsend otp\b',
        r'\byour aadhaar\b',
        r'\baadhaar number\b',
        r'\bpan card number\b',
        r'\bbank account (?:number|details)\b',
        r'\bifsc code\b',
        r'\baccount number\b',
        r'\bnetbanking (?:password|credentials)\b',
        r'\bcard number\b',
        r'\bcvv\b',
        r'\bcredit card details\b',
        r'\bdebit card details\b',
        r'\bshare your password\b',
        r'\blogin credentials\b',
        r'\bprovide your pin\b',
        r'\bwallet details\b',
        r'\bupi id\b',
    ]

    # ------------------------------------------------------------------
    # 3. Unrealistic Offers & Impossible Guarantees
    # ------------------------------------------------------------------
    UNREALISTIC_PATTERNS = [
        r'\bguaranteed job\b',
        r'\b100% placement\b',
        r'\bguaranteed placement\b',
        r'\bno interview (?:needed|required)\b',
        r'\bdirect selection without interview\b',
        r'\bearn per day\b',
        r'\bearn daily\b',
        r'\bearn from day 1\b',
        r'\beasy money\b',
        r'\bsimple copy paste\b',
        r'\bearn (?:rs\.?|inr|₹|\$)?\s*\d{4,}\s*(?:per|a)\s*day\b',
        r'\bno experience no skills needed earn\b',
    ]

    # ------------------------------------------------------------------
    # 4. Urgency & Pressure Tactics
    # ------------------------------------------------------------------
    URGENCY_PATTERNS = [
        r'\blimited seats\b',
        r'\bapply within 1 hour\b',
        r'\burgent hiring today only\b',
        r'\boffer expires (?:today|immediately|in \d+ hours?)\b',
        r'\bhurry only \d+ spots? left\b',
        r'\bimmediate joining without screening\b',
        r'\brush your application\b',
        r'\blast chance today\b',
    ]

    # ------------------------------------------------------------------
    # 5. Off-platform / unsafe contact channels
    # ------------------------------------------------------------------
    OFF_PLATFORM_PATTERNS = [
        r'\bdm on telegram\b',
        r'\bcontact only on whatsapp\b',
        r'\btelegram only\b',
        r'\bjoin telegram channel\b',
        r'\bt\.me\/[a-zA-Z0-9_+]+',
        r'\bwa\.me\/\d+',
        r'\bwhatsapp your resume to \d+\b',
        r'\bdo not email,? message on (?:whatsapp|telegram)\b',
    ]

    # ------------------------------------------------------------------
    # 6. Suspicious Application Instruction Patterns — NEW
    # ------------------------------------------------------------------
    SUSPICIOUS_INSTRUCTIONS_PATTERNS = [
        r'\bpay (?:rs\.?|inr|₹|\$)\s*\d+',
        r'\bsend money\b',
        r'\btransfer amount\b',
        r'\bclick (?:here|this link) to (?:register|apply|pay)',
        r'\bdownload (?:this )?app (?:to|and) (?:apply|register)\b',
        r'\binstall (?:the )?app\b',
        r'\bjoin (?:this )?telegram\b',
        r'\bwhatsapp (?:group|channel)\b',
        r'\bsend your (?:bank|card|account)\b',
    ]

    # ------------------------------------------------------------------
    # 7. Free / disposable public e-mail providers
    # ------------------------------------------------------------------
    FREE_EMAIL_DOMAINS = {
        'gmail.com', 'yahoo.com', 'yahoo.in', 'yahoo.co.in',
        'hotmail.com', 'outlook.com', 'rediffmail.com', 'yopmail.com',
        'mailinator.com', 'tempmail.com', 'proton.me', 'protonmail.com',
    }

    # ------------------------------------------------------------------
    # 8. URL shorteners & suspicious link patterns
    #    (extended with new domains)
    # ------------------------------------------------------------------
    URL_SHORTENERS = [
        r'bit\.ly\/[a-zA-Z0-9]+',
        r'tinyurl\.com\/[a-zA-Z0-9]+',
        r't\.co\/[a-zA-Z0-9]+',
        r'is\.gd\/[a-zA-Z0-9]+',
        r'cutt\.ly\/[a-zA-Z0-9]+',
        r'shorturl\.at\/[a-zA-Z0-9]+',
        r'rb\.gy\/[a-zA-Z0-9]+',
        r'goo\.gl\/[a-zA-Z0-9]+',
        # NEW additions
        r'ow\.ly\/[a-zA-Z0-9]+',
        r'buff\.ly\/[a-zA-Z0-9]+',
        r'clk\.sh\/[a-zA-Z0-9]+',
        r'rebrand\.ly\/[a-zA-Z0-9]+',
        r'lnkd\.in\/[a-zA-Z0-9]+',
        r'mcaf\.ee\/[a-zA-Z0-9]+',
        r'soo\.gd\/[a-zA-Z0-9]+',
        r'youtu\.be\/[a-zA-Z0-9_\-]+',
        r'linktr\.ee\/[a-zA-Z0-9_\-]+',
    ]

    # ------------------------------------------------------------------
    # 9. Raw IP-address URLs
    # ------------------------------------------------------------------
    IP_URL_PATTERN = r'https?:\/\/(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:\/\S*)?'

    # ==================================================================
    # Private helpers
    # ==================================================================

    @classmethod
    def _normalize_url(cls, raw_url):
        """
        Normalize a URL: lowercase scheme + host, validate scheme is
        http or https only.

        Returns the normalised URL string, or None if the URL is
        invalid or uses a disallowed scheme (e.g. javascript:, ftp:).

        NOTE: This method never fetches or visits the URL.
        """
        try:
            parsed = urlparse(raw_url.strip())
            if parsed.scheme not in ('http', 'https', ''):
                return None  # reject non-http schemes
            return parsed.geturl().lower()
        except Exception:
            return None

    @classmethod
    def _check_spam_repetition(cls, text):
        """
        Detect copy-paste spam: returns True when any sentence (split on
        '.', '!', '?') appears 3 or more times in the normalised text.
        """
        sentences = re.split(r'[.!?]', text)
        counts = {}
        for s in sentences:
            key = s.strip().lower()
            if len(key) < 8:   # ignore trivially short fragments
                continue
            counts[key] = counts.get(key, 0) + 1
        return any(v >= 3 for v in counts.values())

    @classmethod
    def _word_bigrams(cls, text):
        """Return a set of word bigrams (2-word tuples) from *text*."""
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 2:
            return set()
        return {(words[i], words[i + 1]) for i in range(len(words) - 1)}

    # ==================================================================
    # Public API
    # ==================================================================

    @classmethod
    def check_duplicate(cls, new_text, existing_texts):
        """
        Compare *new_text* against a list of *existing_texts* using
        word-bigram Jaccard similarity.

        Returns a 3-tuple:
            (is_duplicate: bool, similarity_score: float, matched_index: int | None)

        A posting is considered a duplicate when the Jaccard similarity
        score against any existing text is >= 0.85.

        No external libraries are required; all computation is in-process.
        """
        if not new_text or not existing_texts:
            return False, 0.0, None

        new_bigrams = cls._word_bigrams(new_text)
        if not new_bigrams:
            return False, 0.0, None

        best_score = 0.0
        best_index = None

        for idx, existing in enumerate(existing_texts):
            if not existing:
                continue
            existing_bigrams = cls._word_bigrams(existing)
            if not existing_bigrams:
                continue

            intersection = len(new_bigrams & existing_bigrams)
            union = len(new_bigrams | existing_bigrams)
            score = intersection / union if union else 0.0

            if score > best_score:
                best_score = score
                best_index = idx

        is_dup = best_score >= 0.85
        return is_dup, round(best_score, 4), best_index if is_dup else None

    @classmethod
    def evaluate_posting(cls, internship_data, company=None, existing_descriptions=None):
        """
        Scans an internship posting for scam indicators.

        Parameters
        ----------
        internship_data : dict
            Keys used:
                title, description, responsibilities, eligibility,
                skills_required, contact_email, contact_phone,
                stipend_amount, stipend_type, application_instructions
        company : object, optional
            ORM / dataclass with a ``.website`` attribute.  Used for
            domain-mismatch link checking.
        existing_descriptions : list of str, optional
            When supplied, the posting description is compared against
            these strings for duplicate / recycled-listing detection.

        Returns
        -------
        dict
            risk_score            : int   — 0–100, capped
            risk_level            : str   — 'Low' | 'Medium' | 'High'
            triggered_rules       : list  — each item is a dict with keys
                                           category, rule, weight, severity, detail
            summary_notes         : str
            recommendation        : str
            disclaimer            : str
            requires_human_review : bool
        """
        triggered_rules = []
        raw_score = 0
        weights = cls.RULES_CONFIG['weights']
        thresholds = cls.RULES_CONFIG['thresholds']

        # ------------------------------------------------------------------
        # Extract fields
        # ------------------------------------------------------------------
        title                    = internship_data.get('title', '') or ''
        description              = internship_data.get('description', '') or ''
        responsibilities         = internship_data.get('responsibilities', '') or ''
        eligibility              = internship_data.get('eligibility', '') or ''
        skills                   = internship_data.get('skills_required', '') or ''
        application_instructions = internship_data.get('application_instructions', '') or ''
        contact_email            = (internship_data.get('contact_email') or '').lower().strip()
        contact_phone            = (internship_data.get('contact_phone') or '').strip()  # noqa: F841 – kept for future checks
        stipend_amount           = float(internship_data.get('stipend_amount') or 0.0)
        stipend_type             = internship_data.get('stipend_type', 'paid') or 'paid'

        # Primary text corpus (title + core fields) — lowercased
        full_text = (
            f"{title} {description} {responsibilities} {eligibility} {skills}"
        ).lower()

        # Instructions text is kept separately for the dedicated check but
        # also folded into full_text for PAYMENT / CREDENTIAL scanning.
        instructions_text = application_instructions.lower()
        full_text_with_instr = f"{full_text} {instructions_text}"

        # ------------------------------------------------------------------
        # CHECK 1 — Upfront Payment Demands  (weight: 35, Critical)
        # ------------------------------------------------------------------
        matched_payment = []
        for pattern in cls.PAYMENT_PATTERNS:
            hits = re.findall(pattern, full_text_with_instr, flags=re.IGNORECASE)
            matched_payment.extend(hits)

        if matched_payment:
            weight = weights['payment_demand']
            raw_score += weight
            triggered_rules.append({
                'category': 'Financial Demands',
                'rule': 'Upfront Payment Requested',
                'weight': weight,
                'severity': 'Critical',
                'detail': (
                    f"Detected suspicious upfront payment keywords: "
                    f"{', '.join(list(set(matched_payment))[:3])}. "
                    "Legitimate internships never ask candidates to pay "
                    "registration or deposit fees."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 2 — Credential / Sensitive-Data Requests  (weight: 35, Critical) — NEW
        # ------------------------------------------------------------------
        matched_credentials = []
        for pattern in cls.CREDENTIAL_PATTERNS:
            hits = re.findall(pattern, full_text_with_instr, flags=re.IGNORECASE)
            matched_credentials.extend(hits)

        if matched_credentials:
            weight = weights['credential_request']
            raw_score += weight
            triggered_rules.append({
                'category': 'Data Privacy Violation',
                'rule': 'Sensitive Credential or Financial Data Requested',
                'weight': weight,
                'severity': 'Critical',
                'detail': (
                    f"Posting requests sensitive personal or financial information: "
                    f"{', '.join(list(set(matched_credentials))[:3])}. "
                    "No legitimate internship provider asks for OTPs, card details, "
                    "Aadhaar numbers, or banking credentials."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 3 — Unrealistic Offers & Excessive Stipend  (weight: 25)
        # ------------------------------------------------------------------
        matched_unrealistic = []
        for pattern in cls.UNREALISTIC_PATTERNS:
            hits = re.findall(pattern, full_text, flags=re.IGNORECASE)
            matched_unrealistic.extend(hits)

        is_extreme_stipend = stipend_type == 'paid' and stipend_amount > 60000

        if matched_unrealistic or is_extreme_stipend:
            details = []
            if matched_unrealistic:
                details.append(
                    f"Contains misleading claims: {', '.join(set(matched_unrealistic))}"
                )
            if is_extreme_stipend:
                details.append(
                    f"Unusually high monthly stipend (₹{stipend_amount:,.2f}) for an internship role"
                )
            weight = weights['unrealistic_offer']
            raw_score += weight
            triggered_rules.append({
                'category': 'Offer Credibility',
                'rule': 'Unrealistic Guarantees or Excessive Stipend',
                'weight': weight,
                'severity': 'High',
                'detail': (
                    "; ".join(details)
                    + ". Scammers often bait students with guaranteed jobs and exaggerated payouts."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 4 — Suspicious / Free Contact Channels  (weight: 20)
        # ------------------------------------------------------------------
        suspicious_contact_reasons = []

        if '@' in contact_email:
            domain = contact_email.split('@')[-1]
            if domain in cls.FREE_EMAIL_DOMAINS:
                suspicious_contact_reasons.append(
                    f"Official contact uses generic free email provider (@{domain}) "
                    "instead of an authentic company domain"
                )

        matched_channels = []
        for pattern in cls.OFF_PLATFORM_PATTERNS:
            hits = re.findall(pattern, full_text_with_instr, flags=re.IGNORECASE)
            matched_channels.extend(hits)
        if matched_channels:
            suspicious_contact_reasons.append(
                f"Directs students away from secure channels: "
                f"{', '.join(set(matched_channels))}"
            )

        if suspicious_contact_reasons:
            weight = weights['contact_safety']
            raw_score += weight
            triggered_rules.append({
                'category': 'Contact Safety',
                'rule': 'Suspicious or Unverified Contact Channels',
                'weight': weight,
                'severity': 'Medium-High',
                'detail': "; ".join(suspicious_contact_reasons),
            })

        # ------------------------------------------------------------------
        # CHECK 5 — Suspicious Links & Shorteners  (weight: 20)
        # ------------------------------------------------------------------
        suspicious_links = []

        for shortener_pattern in cls.URL_SHORTENERS:
            hits = re.findall(shortener_pattern, full_text_with_instr, flags=re.IGNORECASE)
            suspicious_links.extend(hits)

        ip_links = re.findall(cls.IP_URL_PATTERN, full_text_with_instr)
        suspicious_links.extend(ip_links)

        # Domain-mismatch check against registered company website
        if company and getattr(company, 'website', None):
            try:
                comp_domain = (
                    urlparse(company.website).netloc.lower().replace('www.', '')
                )
                raw_urls = re.findall(
                    r'https?://[^\s<>"]+|www\.[^\s<>"]+',
                    full_text_with_instr,
                )
                trusted_domains = {'google.com', 'linkedin.com', 'github.com'}
                for raw_u in raw_urls:
                    norm_u = cls._normalize_url(
                        raw_u if raw_u.startswith('http') else 'http://' + raw_u
                    )
                    if norm_u is None:
                        continue
                    u_domain = urlparse(norm_u).netloc.replace('www.', '')
                    if (
                        comp_domain
                        and u_domain
                        and comp_domain not in u_domain
                        and u_domain not in comp_domain
                        and not any(td in u_domain for td in trusted_domains)
                    ):
                        suspicious_links.append(
                            f"External domain ({u_domain}) does not match "
                            f"company domain ({comp_domain})"
                        )
            except Exception:
                pass

        if suspicious_links:
            weight = weights['suspicious_link']
            raw_score += weight
            triggered_rules.append({
                'category': 'Link Verification',
                'rule': 'Shortened or Mismatched External Links',
                'weight': weight,
                'severity': 'Medium-High',
                'detail': (
                    f"Detected suspicious link patterns: "
                    f"{', '.join(list(set(suspicious_links))[:3])}. "
                    "Shortened links often hide malicious or phishing destinations."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 6 — High Urgency & Pressure Tactics  (weight: 15)
        # ------------------------------------------------------------------
        matched_urgency = []
        for pattern in cls.URGENCY_PATTERNS:
            hits = re.findall(pattern, full_text_with_instr, flags=re.IGNORECASE)
            matched_urgency.extend(hits)

        if matched_urgency:
            weight = weights['urgency_pressure']
            raw_score += weight
            triggered_rules.append({
                'category': 'Psychological Pressure',
                'rule': 'Artificial Urgency & Scarcity Tactics',
                'weight': weight,
                'severity': 'Medium',
                'detail': (
                    f"Uses high-pressure urgency words: {', '.join(set(matched_urgency))}. "
                    "Scammers use panic-inducing deadlines to discourage due diligence."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 7 — Vague or Extremely Brief Descriptions  (weight: 15)
        # ------------------------------------------------------------------
        desc_words = description.strip().split()
        is_vague = False
        vague_notes = []

        if len(desc_words) < 30:
            is_vague = True
            vague_notes.append(
                f"Description is extremely brief ({len(desc_words)} words; "
                "minimum 30 words recommended)"
            )
        if not responsibilities or len(responsibilities.strip().split()) < 10:
            is_vague = True
            vague_notes.append("No clear day-to-day responsibilities detailed")
        if not skills or len(skills.strip().split()) < 1:
            is_vague = True
            vague_notes.append("No technical or functional skills specified")

        if is_vague:
            weight = weights['vague_content']
            raw_score += weight
            triggered_rules.append({
                'category': 'Content Quality',
                'rule': 'Vague or Opaque Job Specifications',
                'weight': weight,
                'severity': 'Low-Medium',
                'detail': (
                    "; ".join(vague_notes)
                    + ". Genuine employers outline concrete roles and prerequisites."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 8 — Spam / Copy-Paste Repetition  (weight: 20) — NEW
        # ------------------------------------------------------------------
        if cls._check_spam_repetition(full_text_with_instr):
            weight = weights['spam_repetition']
            raw_score += weight
            triggered_rules.append({
                'category': 'Content Quality',
                'rule': 'Spam Repetition Detected',
                'weight': weight,
                'severity': 'Medium',
                'detail': (
                    "The posting contains the same sentence or phrase repeated "
                    "3 or more times, which is a common indicator of automated "
                    "spam or bulk-posted fraudulent listings."
                ),
            })

        # ------------------------------------------------------------------
        # CHECK 9 — Suspicious Application Instructions  (weight: 20) — NEW
        # ------------------------------------------------------------------
        if instructions_text:
            matched_instr = []
            # Also re-scan instructions through PAYMENT and CREDENTIAL patterns
            for pattern in cls.PAYMENT_PATTERNS + cls.CREDENTIAL_PATTERNS:
                hits = re.findall(pattern, instructions_text, flags=re.IGNORECASE)
                matched_instr.extend(hits)
            for pattern in cls.SUSPICIOUS_INSTRUCTIONS_PATTERNS:
                hits = re.findall(pattern, instructions_text, flags=re.IGNORECASE)
                matched_instr.extend(hits)

            if matched_instr:
                weight = weights['instructions_risk']
                raw_score += weight
                triggered_rules.append({
                    'category': 'Application Instructions',
                    'rule': 'Suspicious Application Instructions',
                    'weight': weight,
                    'severity': 'High',
                    'detail': (
                        f"Application instructions contain risky directives: "
                        f"{', '.join(list(set(matched_instr))[:3])}. "
                        "Legitimate employers do not instruct applicants to pay money, "
                        "install apps, or share sensitive data to apply."
                    ),
                })

        # ------------------------------------------------------------------
        # CHECK 10 — Duplicate / Recycled Listing Detection  (weight: 30) — NEW
        # ------------------------------------------------------------------
        if existing_descriptions:
            compare_text = f"{title} {description}"
            is_dup, sim_score, matched_idx = cls.check_duplicate(
                compare_text, existing_descriptions
            )
            if is_dup:
                weight = weights['duplicate_similarity']
                raw_score += weight
                triggered_rules.append({
                    'category': 'Duplicate Detection',
                    'rule': 'High Similarity to Existing Listing',
                    'weight': weight,
                    'severity': 'High',
                    'detail': (
                        f"This posting is {sim_score * 100:.1f}% similar (bigram Jaccard) "
                        f"to an existing listing (index {matched_idx}). "
                        "Recycled or mass-duplicated listings are a strong indicator "
                        "of coordinated scam campaigns."
                    ),
                })

        # ------------------------------------------------------------------
        # Final Score & Risk Level
        # ------------------------------------------------------------------
        risk_score = min(100, raw_score)

        if risk_score >= thresholds['medium_max'] + 1:   # >= 61
            risk_level = 'High'
            summary_notes = (
                f"HIGH RISK SCAM WARNING: This posting scored {risk_score}/100. "
                f"Severe red flags were detected ({len(triggered_rules)} rules triggered). "
                "Listing has been held for manual administrator review."
            )
            recommendation = "Hold for admin review and do not publish directly to students."
        elif risk_score >= thresholds['low_max'] + 1:    # 31–60
            risk_level = 'Medium'
            summary_notes = (
                f"MODERATE CAUTION: This posting scored {risk_score}/100. "
                f"Some suspicious elements were detected ({len(triggered_rules)} rules triggered). "
                "Published with visible safety caution badges to students."
            )
            recommendation = "Publish with prominent student safety warning banner."
        else:                                             # 0–30
            risk_level = 'Low'
            summary_notes = (
                f"LOW RISK (Score: {risk_score}/100): Passed all automated scam "
                "verification heuristics. No critical red flags detected."
            )
            recommendation = "Approved for standard student browsing."

        return {
            'risk_score':            risk_score,
            'risk_level':            risk_level,
            'triggered_rules':       triggered_rules,
            'summary_notes':         summary_notes,
            'recommendation':        recommendation,
            'disclaimer':            (
                "AI risk assessment only. This result is not proof of fraud or legitimacy."
            ),
            'requires_human_review': risk_level == 'High',
        }
