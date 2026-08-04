#!/usr/bin/env python3
"""
بوت ينشر قصائد وأبيات شعرية كاملة تلقائياً بقناة تيليجرام، مع محتوى خاص:
- كل ساعة: قصيدة/أبيات شعرية كاملة (فصحى أو شعر شعبي عراقي)
- كل يوم جمعة الساعة 7 صباحاً (بتوقيت العراق/السعودية): رسالة "جمعة مباركة"

يقرأ الإعدادات من متغيرات البيئة (Environment Variables):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHANNEL   (مثال: @mahdi09245)
  GEMINI_API_KEY
"""

import os
import sys
import random
import time
from datetime import datetime, timedelta, timezone
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent?key=" + str(GEMINI_API_KEY)
)

# توقيت العراق/السعودية = UTC+3
LOCAL_TZ = timezone(timedelta(hours=3))

# مواضيع مختلفة للتنوع
THEMES = [
    "الفراق والبعد",
    "الوفاء والخيانة",
    "الحكمة وتقلب الدهر",
    "الصبر والقدر",
    "الشوق والانتظار",
    "الاعتزاز بالنفس وعدم الاكتراث",
    "الأمل بعد الألم",
    "التغير والزمن",
    "عزة النفس والكرامة",
]

STYLES = ["اللغة العربية الفصحى", "اللهجة العراقية"]

# كلمات لو انتهى بها النص غالباً معناها انقطع بالمنتصف
_INCOMPLETE_ENDINGS = ("و", "أو", "في", "من", "على", "إلى", "عن", "مع", "لأن", "حتى", "لكن")

# رسائل جمعة مباركة
JUMUA_MESSAGES = [
    "جمعة مباركة على الجميع، تقبل الله منا ومنكم صالح الأعمال",
    "جمعة مباركة، جعلها الله يوم خير وبركة وسعادة على قلوبكم",
    "كل جمعة وأنتم بخير، جمعة مباركة أعادها الله عليكم باليمن والبركات",
    "جمعة مباركة، اللهم اجعل هذا اليوم بداية خير وسعادة لنا جميعاً",
]


def _is_valid_arabic(text: str) -> bool:
    """يتحقق أن النص عربي بالكامل تقريباً، مكتمل، وما ينتهي بحرف عطف/جر."""
    has_english = any(("a" <= ch.lower() <= "z") for ch in text)
    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)
    looks_broken = "(" in text or ")" in text or len(text) < 8
    last_word = text.rstrip("؟!.،").split()[-1] if text.split() else ""
    ends_incomplete = last_word in _INCOMPLETE_ENDINGS
    return has_arabic and not has_english and not looks_broken and not ends_incomplete


def generate_quote() -> str:
    """يطلب من Gemini قصيدة أو أبيات شعرية كاملة ومترابطة (فصحى أو عراقي)."""
    for attempt in range(6):
        if attempt > 0:
            time.sleep(3)  # تأخير بسيط بين المحاولات لتفادي حد الطلبات
            
        theme = random.choice(THEMES)
        style = random.choice(STYLES)

        prompt = (
            "أنت شاعر قدير تكتب لقناة شعرية متخصصة.\n"
            f"اكتب أبياتاً شعرية كاملة ومترابطة (من 3 إلى 5 أبيات) عن موضوع: {theme}.\n\n"
            "الشروط والمطلوب:\n"
            f"1. النمط المطلوب: {style}.\n"
            "2. إذا كان النمط (اللغة العربية الفصحى): اكتب شعر عمودي مقفى بوزن وقافية واضحين وصدر وعجز.\n"
            "3. إذا كان النمط (اللهجة العراقية): اكتب شعر شعبي عراقي أصيل متكامل (قصيدة شعبية، أو أبوذية، أو دارمي متناسق، أو زهيري).\n"
            "4. يمنع منعاً باتاً خلط الفصحى بالعامية، الالتزام بالأسلوب المختار فقط.\n"
            "5. ممنوع استخدام أي كلمات أو حروف إنجليزية.\n"
            "6. يجب أن تكون الأبيات مكتملة المعنى والبناء ولها نهاية واضحة وقوية.\n"
            "7. أعطني الأبيات الشعرية مباشرة بدون أي مقدمات أو شرح (مثل: إليك القصيدة) وبدون علامات تنصيص."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 700,
            },
        }

        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"رد Gemini غير متوقع: {data}") from e

        text = text.strip('"').strip("«»").strip()

        if _is_valid_arabic(text):
            return text

    # نص احتياطي كامل في حال فشل التوليد بعد 6 محاولات
    return (
        "رَفَعتُ نَفسي عَن هَوانِ وِدادِكُم\n"
        "فَالجَبلُ لا يَهوي لِغيرِ ذُراهُ\n"
        "وَتَرَكتُ ما بَينِي وَبَينَكُمُ الهَوى\n"
        "عِزّاً لِنَفسِي كَي يَعُودَ صَداهُ"
    )


def get_content_for_now() -> str:
    """يحدد نوع المحتوى المناسب حسب الوقت الحالي."""
    now = datetime.now(LOCAL_TZ)
    is_friday = now.weekday() == 4  # الجمعة = 4 بترقيم بايثون
    is_seven_am = now.hour == 7

    if is_friday and is_seven_am:
        return random.choice(JUMUA_MESSAGES)

    return generate_quote()


def escape_html(text: str) -> str:
    """تجهيز النص ليكون آمناً للعرض بـ HTML في تيليجرام."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def post_to_telegram(text: str) -> None:
    """ينشر القصيدة بالقناة داخل اقتباس (blockquote)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    lines = text.split("\n")
    quoted_lines = "\n".join(escape_html(line) for line in lines if line.strip())
    html_text = f"<blockquote>{quoted_lines}</blockquote>"

    payload = {
        "chat_id": TELEGRAM_CHANNEL,
        "text": html_text,
        "parse_mode": "HTML",
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"فشل النشر بتيليجرام: {result}")
    print("تم النشر بنجاح:\n", text)


def main():
    missing = [
        name
        for name, val in [
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHANNEL", TELEGRAM_CHANNEL),
            ("GEMINI_API_KEY", GEMINI_API_KEY),
        ]
        if not val
    ]
    if missing:
        print("متغيرات ناقصة:", ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    try:
        content = get_content_for_now()
        post_to_telegram(content)
    except Exception as e:
        print("خطأ:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
