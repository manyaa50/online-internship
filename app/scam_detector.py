import re
from urllib.parse import urlparse


class ScamDetector:
    """
    Automated Scam Detection Engine for Internship Postings.
    Evaluates postings using weighted rule-based and pattern-based heuristics.
    """

    # 1. Upfront Payment & Financial Demands (High Weight)
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

    # 2. Unrealistic Offers & Impossible Guarantees (High Weight)
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

    # 3. Urgency & Pressure Tactics (Medium Weight)
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

    # 4. WhatsApp / Telegram only or suspicious channel redirects
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

    # 5. Free public email domains (suspicious when used for company postings)
    FREE_EMAIL_DOMAINS = {
        'gmail.com', 'yahoo.com', 'yahoo.in', 'yahoo.co.in',
        'hotmail.com', 'outlook.com', 'rediffmail.com', 'yopmail.com',
        'mailinator.com', 'tempmail.com', 'proton.me', 'protonmail.com'
    }

    # 6. URL shorteners & suspicious links
    URL_SHORTENERS = [
        r'bit\.ly\/[a-zA-Z0-9]+',
        r'tinyurl\.com\/[a-zA-Z0-9]+',
        r't\.co\/[a-zA-Z0-9]+',
        r'is\.gd\/[a-zA-Z0-9]+',
        r'cutt\.ly\/[a-zA-Z0-9]+',
        r'shorturl\.at\/[a-zA-Z0-9]+',
        r'rb\.gy\/[a-zA-Z0-9]+',
        r'goo\.gl\/[a-zA-Z0-9]+'
    ]

    IP_URL_PATTERN = r'https?:\/\/(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:\/\S*)?'

    @classmethod
    def evaluate_posting(cls, internship_data, company=None):
        """
        Scans internship title, description, stipend, contact details and company data.
        Returns:
            dict with:
                - risk_score: int (0 to 100)
                - risk_level: str ('Low', 'Medium', 'High')
                - triggered_rules: list of dicts with rule, weight, detail
                - summary_notes: str
                - recommendation: str
        """
        triggered_rules = []
        raw_score = 0

        title = internship_data.get('title', '')
        description = internship_data.get('description', '')
        responsibilities = internship_data.get('responsibilities', '')
        eligibility = internship_data.get('eligibility', '')
        skills = internship_data.get('skills_required', '')
        contact_email = (internship_data.get('contact_email') or '').lower().strip()
        contact_phone = (internship_data.get('contact_phone') or '').strip()
        stipend_amount = float(internship_data.get('stipend_amount') or 0.0)
        stipend_type = internship_data.get('stipend_type', 'paid')

        full_text = f"{title} {description} {responsibilities} {eligibility} {skills}".lower()

        # -------------------------------------------------------------
        # CHECK 1: Upfront Payment Demands (Weight: 35)
        # -------------------------------------------------------------
        matched_payment_phrases = []
        for pattern in cls.PAYMENT_PATTERNS:
            matches = re.findall(pattern, full_text, flags=re.IGNORECASE)
            if matches:
                matched_payment_phrases.extend(matches)
        
        if matched_payment_phrases:
            unique_matches = list(set(matched_payment_phrases))[:3]
            weight = 35
            raw_score += weight
            triggered_rules.append({
                'category': 'Financial Demands',
                'rule': 'Upfront Payment Requested',
                'weight': weight,
                'severity': 'Critical',
                'detail': f"Detected suspicious upfront payment keywords: {', '.join(unique_matches)}. Legitimate internships never ask candidates to pay registration or deposit fees."
            })

        # -------------------------------------------------------------
        # CHECK 2: Unrealistic Offers & Job Guarantees (Weight: 25)
        # -------------------------------------------------------------
        matched_unrealistic = []
        for pattern in cls.UNREALISTIC_PATTERNS:
            matches = re.findall(pattern, full_text, flags=re.IGNORECASE)
            if matches:
                matched_unrealistic.extend(matches)
        
        # Check extremely high stipend (> INR 60,000/mo for general internship posting)
        is_extreme_stipend = False
        if stipend_type == 'paid' and stipend_amount > 60000:
            is_extreme_stipend = True

        if matched_unrealistic or is_extreme_stipend:
            details = []
            if matched_unrealistic:
                details.append(f"Contains misleading claims: {', '.join(set(matched_unrealistic))}")
            if is_extreme_stipend:
                details.append(f"Unusually high monthly stipend (₹{stipend_amount:,.2f}) for an internship role")
            
            weight = 25
            raw_score += weight
            triggered_rules.append({
                'category': 'Offer Credibility',
                'rule': 'Unrealistic Guarantees or Excessive Stipend',
                'weight': weight,
                'severity': 'High',
                'detail': "; ".join(details) + ". Scammers often bait students with guaranteed jobs and exaggerated payouts."
            })

        # -------------------------------------------------------------
        # CHECK 3: Suspicious & Free Contact Channels (Weight: 20)
        # -------------------------------------------------------------
        suspicious_contact_reasons = []

        # Check free email domain on company postings
        if '@' in contact_email:
            domain = contact_email.split('@')[-1]
            if domain in cls.FREE_EMAIL_DOMAINS:
                suspicious_contact_reasons.append(
                    f"Official contact uses generic free email provider (@{domain}) instead of an authentic company domain"
                )

        # Check off-platform messaging redirects
        matched_channels = []
        for pattern in cls.OFF_PLATFORM_PATTERNS:
            found = re.findall(pattern, full_text, flags=re.IGNORECASE)
            if found:
                matched_channels.extend(found)
        if matched_channels:
            suspicious_contact_reasons.append(
                f"Directs students away from secure channels: {', '.join(set(matched_channels))}"
            )

        if suspicious_contact_reasons:
            weight = 20
            raw_score += weight
            triggered_rules.append({
                'category': 'Contact Safety',
                'rule': 'Suspicious or Unverified Contact Channels',
                'weight': weight,
                'severity': 'Medium-High',
                'detail': "; ".join(suspicious_contact_reasons)
            })

        # -------------------------------------------------------------
        # CHECK 4: Suspicious Links & Shorteners (Weight: 20)
        # -------------------------------------------------------------
        suspicious_links = []
        for shortener in cls.URL_SHORTENERS:
            found = re.findall(shortener, full_text, flags=re.IGNORECASE)
            if found:
                suspicious_links.extend(found)
        
        ip_links = re.findall(cls.IP_URL_PATTERN, full_text)
        if ip_links:
            suspicious_links.extend(ip_links)

        # Domain mismatch check if company website is provided
        if company and company.website:
            try:
                comp_domain = urlparse(company.website).netloc.lower().replace('www.', '')
                # Find all URLs in full_text
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', full_text)
                for u in urls:
                    u_domain = urlparse(u if u.startswith('http') else 'http://' + u).netloc.lower().replace('www.', '')
                    if comp_domain and u_domain and comp_domain not in u_domain and u_domain not in comp_domain:
                        if not any(trusted in u_domain for trusted in ['google.com', 'linkedin.com', 'github.com']):
                            suspicious_links.append(f"External domain ({u_domain}) does not match company domain ({comp_domain})")
            except Exception:
                pass

        if suspicious_links:
            weight = 20
            raw_score += weight
            triggered_rules.append({
                'category': 'Link Verification',
                'rule': 'Shortened or Mismatched External Links',
                'weight': weight,
                'severity': 'Medium-High',
                'detail': f"Detected suspicious link patterns: {', '.join(set(suspicious_links)[:3])}. Shortened links often hide malicious or phishing destinations."
            })

        # -------------------------------------------------------------
        # CHECK 5: High Urgency and Pressure Tactics (Weight: 15)
        # -------------------------------------------------------------
        matched_urgency = []
        for pattern in cls.URGENCY_PATTERNS:
            found = re.findall(pattern, full_text, flags=re.IGNORECASE)
            if found:
                matched_urgency.extend(found)

        if matched_urgency:
            weight = 15
            raw_score += weight
            triggered_rules.append({
                'category': 'Psychological Pressure',
                'rule': 'Artificial Urgency & Scarcity Tactics',
                'weight': weight,
                'severity': 'Medium',
                'detail': f"Uses high-pressure urgency words: {', '.join(set(matched_urgency))}. Scammers use panic-inducing deadlines to discourage due diligence."
            })

        # -------------------------------------------------------------
        # CHECK 6: Vague or Extremely Brief Descriptions (Weight: 15)
        # -------------------------------------------------------------
        words = description.strip().split()
        is_vague = False
        vague_notes = []

        if len(words) < 30:
            is_vague = True
            vague_notes.append(f"Description is extremely brief ({len(words)} words; minimum 30 words recommended)")
        if not responsibilities or len(responsibilities.strip().split()) < 10:
            is_vague = True
            vague_notes.append("No clear day-to-day responsibilities detailed")
        if not skills or len(skills.strip().split()) < 1:
            is_vague = True
            vague_notes.append("No technical or functional skills specified")

        if is_vague:
            weight = 15
            raw_score += weight
            triggered_rules.append({
                'category': 'Content Quality',
                'rule': 'Vague or Opaque Job Specifications',
                'weight': weight,
                'severity': 'Low-Medium',
                'detail': "; ".join(vague_notes) + ". Genuine employers outline concrete roles and prerequisites."
            })

        # -------------------------------------------------------------
        # Final Score Aggregation & Risk Level Categorization
        # -------------------------------------------------------------
        risk_score = min(100, raw_score)

        if risk_score >= 61:
            risk_level = 'High'
            summary_notes = (
                f"HIGH RISK SCAM WARNING: This posting scored {risk_score}/100. "
                f"Severe red flags were detected ({len(triggered_rules)} rules triggered). "
                "Listing has been held for manual administrator review."
            )
            recommendation = "Hold for admin review and do not publish directly to students."
        elif risk_score >= 31:
            risk_level = 'Medium'
            summary_notes = (
                f"MODERATE CAUTION: This posting scored {risk_score}/100. "
                f"Some suspicious elements were detected ({len(triggered_rules)} rules triggered). "
                "Published with visible safety caution badges to students."
            )
            recommendation = "Publish with prominent student safety warning banner."
        else:
            risk_level = 'Low'
            summary_notes = (
                f"LOW RISK (Score: {risk_score}/100): Passed all automated scam verification heuristics. "
                "No critical red flags detected."
            )
            recommendation = "Approved for standard student browsing."

        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'triggered_rules': triggered_rules,
            'summary_notes': summary_notes,
            'recommendation': recommendation
        }
