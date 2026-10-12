# -*- coding: utf-8 -*-
"""
TeleHarvester Pro — High-Precision Drop & Account Detection Engine
Employs heuristic parsing, token analysis, and NLP regex to isolate real drops from spam.
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("TeleHarvester.Filter")

# Domains of coupon scrapers, link shortener farms, and shopping portals to strictly block
BLOCKED_DOMAINS = [
    'freecourse.io',
    'udemy.com',
    'coursecouponclub.com',
    'discudemy.com',
    'tutorialbar.com',
    'couponscorpion.com',
    'yofreesamples.com',
    'real.discount',
    'coursevania.com',
    'onlinecourses.ooo',
    'geeksgod.com',
    'enext.in',
    'aliexpress.com',
    's.click.aliexpress.com',
    'temu.com',
    'temu.to',
    'shein.com',
    'amazon.com',
    'jumia.dz',
    'jumia.com',
    'ouedkniss.com'
]

# Patterns for marketing noise and course spam
COURSE_SCRAPER_PATTERNS = [
    r'enrolls?\s+left',
    r'free\s*-\s*\d+\s+enrolls',
    r'coupon\s*code\s*[:-]',
    r'100%\s*off\s*coupon',
    r'100%\s*off\s*course',
    r'bestseller\s+course',
    r'this\s+comprehensive\s+course',
    r'take\s+you\s+from\s+beginner\s+to',
    r'mastering\s+(microsoft\s+)?(word|excel|powerpoint)',
    r'learn\s+graphic\s+design',
    r'all\s+in\s+one\s+comprehensive\s+course',
    r'hours\s+on-demand\s+video',
    r'certificate\s+of\s+completion\s+included',
    r'تخفيض\s+100%',
    r'كوبون\s+يوديمي',
    r'كورس\s+مجاني',
    r'دورة\s+تدريبية\s+مجانية',
    r'سارع\s+قبل\s+انتهاء\s+الكوبون',
]

# Patterns identifying questions, help requests, or begging across Arabic, Algerian Dialect, & English
QUESTION_PATTERNS = [
    # Dialectal Arabic
    r'\b(شكون|شكون\s+لي)\s+(عندو|عنده|يقدر|يمدلي|معاه|يعطيني|يعرف|شغال)\b',
    r'\bكاين\s+(لي\s+عندو|عندو|شكون|كود|حساب|رابط|طريقة)\b',
    r'\bكاش\s+(كانفا|حساب|كود|تفعيل|رابط|كاب\s*كات|جيميني)\b',
    r'\bمين\s+(عنده|عندو|معاه|يقدر|يعرف|معه)\b',
    r'\bمن\s+(عنده|لديه|يملك|يقدر|يستطيع|يعرف)\b',
    r'\bهل\s+(يوجد|أجد|من|عندكم|أحد|في|شغال|متاح|يعمل|هناك)\b',
    r'\b(محتاج|بدي|أريد|ابحث\s+عن|ابغي|عاوز|نحوس\s+على)\s+(رابط|كود|حساب|تفعيل|دعوة|كانفا|جيميني|كاب\s*كات|كورسيرا|canva|gemini|capcut)\b',
    r'\b(ممكن|افيدونا|يفيدنا|فيدونا|تعيشوا|يعيشكم|بالله)\s+(برابط|بحساب|بكود|بتفعيل|رابط|كود|حساب|كانفا|canva|gemini|capcut)\b',
    r'\b(طريقة|كيفية|شرح|كيف)\s+(تفعيل|الحصول|اشترك|افعل|احصل|تثبيت|استعمال)\b',
    r'\bعندكم\s+(كود|حساب|رابط|تفعيل)\b',
    r'\b(اي|أي)\s+(شخص|واحد|حد)\s+(عنده|معاه|يقدر)\b',
    r'\b(أحد|احد)\s+(عنده|معه|يعرف)\b',
    
    # English
    r'\bwho\s+(has|have|needs|can|wants|got|is)\b',
    r'\banyone\s+(have|has|got|knows|can|share)\b',
    r'\bdoes\s+anyone\s+(have|know|got)\b',
    r'\bis\s+there\s+any\s+(link|account|code|way)\b',
    r'\bhow\s+to\s+(get|activate|bypass|use|obtain)\b',
    r'\bcan\s+(someone|anyone|you)\s+(give|share|send|provide)\b',
    r'\b(need|want|looking\s+for)\s+(a\s+)?(canva|gemini|capcut|coursera|account|pro|invite|link)\b',
    r'\bplease\s+(give|send|share|help)\b',
    r'\bany\s+working\s+(canva|gemini|capcut|link|code)\b',
    r'\bwhere\s+can\s+i\s+get\b',
]

URL_REGEX = re.compile(r'https?://[^\s<>\"\')]+', re.IGNORECASE)
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
COMBO_REGEX = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\s*[:|/]\s*([^\s]{4,})')

TEMP_MAIL_DOMAINS = [
    'mail.tm', 'web-library.net', 'temp-mail.org', 'temp-mail.io',
    '10minutemail.com', 'yopmail.com', 'guerrillamail.com', 'mohmal.com',
    'emailondeck.com', 'generator.email', 'fakemail.net', 'tempmail.net'
]

def extract_combos(text: str) -> List[Dict[str, str]]:
    """Extract email:password credential pairs with support for multi-line and tagged formats."""
    combos = []
    
    # Format 1: Tagged lines (Email: ... \n Password: ...)
    pipe_email = re.search(r'(?:Email|User|Account|حساب|إيميل|البريد)\s*:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text, re.I)
    coursera_pw = re.search(r'(?:Coursera\s+Password|Coursera\s+Pass|كلمة\s*مرور\s*كورسيرا|باسورد\s*كورسيرا)\s*:\s*([^\s|]+)', text, re.I)
    gen_pw = re.search(r'(?:Password|Pass|كلمة\s*المرور|الباسورد|باسورد|pwd)\s*:\s*([^\s|]+)', text, re.I)
    email_pw = re.search(r'(?:Email\s+Password|Email\s+Pass|كلمة\s*مرور\s*الإيميل)\s*:\s*([^\s|]+)', text, re.I)
    
    if pipe_email:
        em = pipe_email.group(1).strip()
        pw = None
        if coursera_pw:
            pw = coursera_pw.group(1).strip()
        elif gen_pw:
            pw = gen_pw.group(1).strip()
        elif email_pw:
            pw = email_pw.group(1).strip()
        if pw:
            combos.append({'email': em, 'password': pw})

    # Format 2: Direct user:pass or email:pass delimited by colon
    for match in re.finditer(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\s*[:]\s*([^\s|]{3,})', text):
        em = match.group(1).strip()
        pw = match.group(2).strip()
        if not any(c['email'] == em for c in combos):
            combos.append({'email': em, 'password': pw})

    # Format 3: Consecutive lines
    lines = text.split('\n')
    for i in range(len(lines) - 1):
        line1 = lines[i].strip()
        line2 = lines[i+1].strip()
        if re.search(r'(?:email|user|login|حساب|إيميل|بريد)\s*:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', line1, re.I):
            em_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', line1, re.I)
            if em_match:
                em = em_match.group(1)
                pw_match = re.search(r'(?:pass|password|pwd|كلمة\s*المرور|الباسورد|باسورد)\s*:\s*([^\s|]+)', line2, re.I)
                if pw_match:
                    pw = pw_match.group(1).strip()
                    if not any(c['email'] == em for c in combos):
                        combos.append({'email': em, 'password': pw})

    return combos

def is_question_or_begging(text: str) -> bool:
    """Identify if the post is merely an inquiry, complaint, or begging."""
    clean = text.strip()
    if len(clean) < 120 and ('?' in clean or '؟' in clean or '👀' in clean):
        for pattern in QUESTION_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE):
                return True

    for pattern in QUESTION_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            has_official = any(
                dom in clean.lower() for dom in [
                    'serviceactivation.google.com',
                    'canva.com/brand/join',
                    'canva.com/join',
                    'capcut.com/t/',
                    'coursera.org/programs/'
                ]
            )
            has_combo = bool(COMBO_REGEX.search(clean))
            if not has_official and not has_combo:
                return True
    return False

def is_course_scraper_spam(text: str, links: List[str]) -> bool:
    """Detect automated coupon aggregators."""
    t_lower = text.lower()
    for link in links:
        if any(bd in link.lower() for bd in BLOCKED_DOMAINS):
            return True

    for pattern in COURSE_SCRAPER_PATTERNS:
        if re.search(pattern, t_lower, re.IGNORECASE):
            has_official = any(
                dom in t_lower for dom in [
                    'serviceactivation.google.com',
                    'canva.com/brand/join',
                    'capcut.com/t/',
                    'coursera.org/programs/'
                ]
            )
            if not has_official:
                return True
    return False

def inspect_and_filter_message(text: str, source_label: str = "") -> Optional[List[Dict[str, Any]]]:
    """
    High-precision parser: Analyzes message content and extracts valid drops.
    Returns structured findings list or None if rejected.
    """
    if not text or not text.strip():
        return None

    clean_text = text.strip()
    lower_text = clean_text.lower()

    raw_links = URL_REGEX.findall(clean_text)
    links = [re.sub(r'[\.,\?!:;]+$', '', l) for l in raw_links]
    emails = EMAIL_REGEX.findall(clean_text)
    combos = extract_combos(clean_text)
    codes = re.findall(r'\b[A-Z0-9]{6,24}\b', clean_text)

    # 1. Reject checks
    if is_course_scraper_spam(clean_text, links):
        logger.debug(f"Rejected: course spam from [{source_label}]")
        return None

    if is_question_or_begging(clean_text):
        logger.debug(f"Rejected: question/begging from [{source_label}]")
        return None

    findings = []

    # Category A: Google AI / Gemini Advanced
    google_links = [
        l for l in links if any(
            d in l.lower() for d in [
                'serviceactivation.google.com',
                'one.google.com/offer',
                'one.google.com/promo',
                'one.google.com/redeem',
                'g.co/gemini',
                'g.co/one'
            ]
        )
    ]
    if google_links or (any(k in lower_text for k in ['gemini advanced', 'google one 2tb', 'تفعيل جيميني', 'اشتراك gemini']) and (links or combos)):
        findings.append({
            'category': 'Google AI / Gemini Advanced',
            'title': 'رابط تفعيل Google Gemini Advanced / Google One مباشر!',
            'emails': emails,
            'combos': combos,
            'links': google_links if google_links else [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
            'codes': codes,
            'raw': clean_text
        })
        return findings

    # Category B: Canva Pro / Edu Team
    canva_links = [
        l for l in links if any(
            c in l.lower() for c in ['canva.com/brand/join', 'canva.com/join', 'canva.link', 'partner.canva.com']
        )
    ]
    is_canva = False
    if canva_links:
        is_canva = True
    elif 'canva' in lower_text:
        keywords = [
            'فريق كانفا', 'انضمام لفريق كانفا', 'دعوة كانفا', 'رابط كانفا برو',
            'كانفا تعليمي', 'canva team invite', 'canva pro invite', 'join canva pro'
        ]
        if (any(k in lower_text for k in keywords) and (links or combos)) or (combos and 'canva' in lower_text):
            is_canva = True

    if is_canva:
        findings.append({
            'category': 'Canva Pro / Edu Team',
            'title': 'دعوة فريق أو حساب Canva Pro رسمي وشغال!',
            'emails': emails,
            'combos': combos,
            'links': canva_links if canva_links else [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
            'codes': codes,
            'raw': clean_text
        })
        return findings

    # Category C: CapCut Pro
    capcut_links = [
        l for l in links if any(cp in l.lower() for cp in ['capcut.com/t/', 'capcut.com/space/', 'matakaw.web.id', 'capcut-pro'])
    ]
    if capcut_links or ('capcut' in lower_text and (links or combos)):
        findings.append({
            'category': 'CapCut Pro',
            'title': 'مساحة عمل أو ترخيص CapCut Pro تم رصده!',
            'emails': emails,
            'combos': combos,
            'links': capcut_links if capcut_links else [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
            'codes': codes,
            'raw': clean_text
        })
        return findings

    # Category D: Coursera Plus / Campus
    coursera_links = [
        l for l in links if any(cr in l.lower() for cr in ['coursera.org/programs/', 'coursera.org/invitation/', 'coursera.org/for-campus/'])
    ]
    if coursera_links or ('coursera' in lower_text and (links or combos)):
        findings.append({
            'category': 'Coursera Plus / Campus',
            'title': 'دعوة برنامج Coursera أو حساب رسمي تم رصده!',
            'emails': emails,
            'combos': combos,
            'links': coursera_links if coursera_links else [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
            'codes': codes,
            'raw': clean_text
        })
        return findings

    # Category E: Verified Credentials (Combos: Email:Password drops)
    if combos:
        services_map = {
            'chatgpt': 'ChatGPT Plus / Team',
            'openai': 'OpenAI / ChatGPT',
            'claude': 'Anthropic Claude Pro',
            'perplexity': 'Perplexity Pro',
            'nordvpn': 'NordVPN Premium',
            'expressvpn': 'ExpressVPN Premium',
            'xv-check': 'ExpressVPN Premium',
            'xv check': 'ExpressVPN Premium',
            'spotify': 'Spotify Premium',
            'netflix': 'Netflix Premium',
            'jetbrains': 'JetBrains All Products',
            'figma': 'Figma Pro / Edu',
            'grammarly': 'Grammarly Premium',
            'heygen': 'HeyGen AI'
        }
        matched = None
        for k, v in services_map.items():
            if k in lower_text:
                matched = v
                break
        
        if matched:
            findings.append({
                'category': matched,
                'title': f'حسابات ومعلومات دخول {matched} شغالة!',
                'emails': emails,
                'combos': combos,
                'links': [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
                'codes': codes,
                'raw': clean_text
            })
            return findings

    # Category F: Temp-Mail Drops
    if any(td in lower_text for td in TEMP_MAIL_DOMAINS) and (emails or combos or links):
        findings.append({
            'category': 'Disposable Temp-Mail Account',
            'title': 'بريد مؤقت أو حساب مرتبط بـ Temp-Mail تم رصده!',
            'emails': emails,
            'combos': combos,
            'links': [l for l in links if not any(b in l.lower() for b in BLOCKED_DOMAINS)],
            'codes': codes,
            'raw': clean_text
        })
        return findings

    return None
