#!/usr/bin/env python3
"""
بوت ينشر خواطر/أبيات قصيرة تلقائياً بقناة تيليجرام، مع محتوى خاص:
- كل ساعة: خاطرة/بيت شعر عربي (فصيح أو عراقي)
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

# مواضيع مختلفة عشان المحتوى يتنوع كل يوم ولا يتكرر بنفس النمط
THEMES = [
    "الفراق والبعد",
    "الوفاء والخيانة",
    "الحكمة وتقلب الدهر",
    "الصبر والقدر",
    "الشوق والانتظار",
    "الاعتزاز بالنفس وعدم الاكتراث",
    "الأمل بعد الألم",
    "التغير والزمن",
]

EXAMPLES = [
    "سهرت الليالي لعيونك تاليها تسهر لعيون غيري؟",
    "احسّنتَ لهم دهراً، و اسأت لهم يوم، نسوا الدهر و تذكرو اليوم!",
    "ومَا فَائِدةُ الدّموعُ إِنِ كَانَتِ الِاقدَارَ مُكتُوبَة",
    "من تكدر تحط عينك و تباوع على الشمس يلا حط عينك بعيني",
    "لا شيء يدوم للابد",
]

STYLES = ["اللغة العربية الفصحى", "اللهجة العراقية"]

# كلمات لو انتهى بها النص غالباً معناها انقطع بالمنتصف (حرف عطف/جر)
_INCOMPLETE_ENDINGS = ("و", "أو", "في", "من", "على", "إلى", "عن", "مع", "لأن", "حتى", "لكن")

# رسائل جمعة مباركة (يُختار منها عشوائياً)
JUMUA_MESSAGES = [
    "جمعة مباركة على الجميع، تقبل الله منا ومنكم صالح الأعمال",
    "جمعة مباركة، جعلها الله يوم خير وبركة وسعادة على قلوبكم",
    "كل جمعة وأنتم بخير، جمعة مباركة أعادها الله عليكم باليمن والبركات",
    "جمعة مباركة، اللهم اجعل هذا اليوم بداية خير وسعادة لنا جميعاً",
]


def _is_valid_arabic(text: str) -> bool:
    """يتحقق أن النص عربي بالكامل تقريباً، مكتمل، قصير، وما ينتهي بحرف عطف/جر."""
    has_english = any(("a" <= ch.lower() <= "z") for ch in text)
    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)
    looks_broken = "(" in text or ")" in text or len(text) < 8
    word_count = len(text.split())
    too_long = word_count > 14  # حماية إضافية ضد النصوص الطويلة المعرّضة للانقطاع
    last_word = text.rstrip("؟!.،").split()[-1] if text.split() else ""
    ends_incomplete = last_word in _INCOMPLETE_ENDINGS
    return (
        has_arabic
        and not has_english
        and not looks_broken
        and not too_long
        and not ends_incomplete
    )


def generate_quote() -> str:
    """يطلب من Gemini نص عربي (فصيح أو عراقي، بدون خلط) كامل ومترابط، بدون حد أقصى للطول."""
    for attempt in range(6):
        if attempt > 0:
            time.sleep(3)  # تأخير بسيط بين المحاولات لتفادي حد الطلبات بالدقيقة
        theme = random.choice(THEMES)
        style = random.choice(STYLES)
        examples_text = "\n".join(f"- {ex}" for ex in EXAMPLES)
        prompt = (
            "أنت شاعر عراقي/عربي تكتب لقناة تيليجرام مختصة بالشعر والخواطر المؤثرة.\n"
            "أمثلة حقيقية من أسلوب القناة (للإلهام فقط، لا تنسخها):\n"
            f"{examples_text}\n\n"
            f"اكتب نصاً عربياً جديداً تماماً عن موضوع: {theme}.\n"
            "المطلوب:\n"
            f"- اكتب النص بأسلوب واحد فقط بالكامل من أوله لآخره: {style}. "
            "ممنوع منعاً باتاً خلط الفصحى مع العامية بنفس النص.\n"
            "- ممنوع منعاً باتاً أي حرف أو كلمة إنجليزية.\n"
            "- نص واحد قصير جداً (10 كلمات كحد أقصى)، مكتمل المعنى تماماً من أوله لآخره.\n"
            "- اكتبه كجملة نثرية واحدة مستقلة بذاتها، وليس على شكل بيت شعر بشطرين "
            "(شطر أول وشطر ثانٍ مرتبطين بفاصلة). ممنوع تقسيم الفكرة إلى جزأين.\n"
            "- لا تحاول إطالة الجملة أو إضافة جزء ثانٍ لها مهما كان.\n"
            "- بلاغة وقوة تعبير (تشبيه أو مفارقة أو حكمة).\n"
            "- بدون علامات تنصيص، وبدون كلمة 'خاطرة' أو 'قصيدة' أو 'جملة'.\n"
            "- بدون أي مقدمات أو تعليقات أو ترجمة.\n"
            "- أعطني النص العربي مباشرة بدون أي شيء آخر."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 250,
            },
        }

        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        try:
            candidate = data["candidates"][0]
            text = candidate["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"رد Gemini غير متوقع: {data}") from e

        # لو النص انقطع بسبب حد الطول (مو لأنه خلص طبيعياً)، نتجاهله ونعيد المحاولة
        finish_reason = candidate.get("finishReason", "")
        if finish_reason not in ("STOP", ""):
            continue

        text = text.strip('"').strip("«»").strip()

        if _is_valid_arabic(text):
            return text

    return "الأيام تمضي وتبقى الذكرى وحدها شاهدة على ما كان"


def get_content_for_now() -> str:
    """يحدد نوع المحتوى المناسب حسب الوقت الحالي: جمعة مباركة يوم الجمعة، خاطرة عادية باقي الأوقات."""
    now = datetime.now(LOCAL_TZ)
    is_friday = now.weekday() == 4  # الجمعة = 4 بترقيم بايثون (الاثنين=0)
    is_seven_am = now.hour == 7

    if is_friday and is_seven_am:
        return random.choice(JUMUA_MESSAGES)

    return generate_quote()


def post_to_telegram(text: str) -> None:
    """ينشر النص بالقناة على شكل اقتباس (blockquote)."""
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
    print("تم النشر بنجاح:", text)


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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
