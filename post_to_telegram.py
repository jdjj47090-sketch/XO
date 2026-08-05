#!/usr/bin/env python3
"""
بوت ينشر خواطر/أبيات قصيرة تلقائياً بقناة تيليجرام، مع محتوى خاص:
- كل ساعة: خاطرة/بيت شعر عربي (فصيح أو عراقي)
- كل يوم جمعة الساعة 7 صباحاً (بتوقيت العراق/السعودية): رسالة "جمعة مباركة"

يقرأ الإعدادات من متغيرات البيئة (Environment Variables):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHANNEL   (مثال: @mahdi09245)
  GROQ_API_KEY
"""

import os
import sys
import random
import time
from datetime import datetime, timedelta, timezone
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

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

EXAMPLES_BY_STYLE = {
    "اللغة العربية الفصحى": [
        "ومَا فَائِدةُ الدّموعُ إِنِ كَانَتِ الِاقدَارَ مُكتُوبَة",
        "رَفَعتُ نَفسي عَن هَوانِ وِدادِكُم فَالجَبلُ لا يَهوي لِغيرِ ذُراهُ",
        "احسّنتَ لهم دهراً، و اسأت لهم يوم، نسوا الدهر و تذكرو اليوم",
    ],
    "اللهجة العراقية": [
        "سهرت الليالي لعيونك تاليها تسهر لعيون غيري؟",
        "من تكدر تحط عينك و تباوع على الشمس يلا حط عينك بعيني",
        "تفگة وبالَيَمن تقنعني ما مَسحوب؟ حَتى اطفال رضّع ساحبه أقسامك",
    ],
}

STYLES = list(EXAMPLES_BY_STYLE.keys())

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
    """يتحقق أن النص عربي بالكامل تقريباً، مكتمل، وما ينتهي بحرف عطف/جر."""
    has_english = any(("a" <= ch.lower() <= "z") for ch in text)
    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)
    looks_broken = "(" in text or ")" in text or len(text) < 8
    word_count = len(text.split())
    too_long = word_count > 60  # حماية فقط ضد الفقرات المبالغ بطولها
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
    """يطلب من Groq نص عربي (فصيح أو عراقي، بدون خلط) كامل ومترابط، يسمح بأبيات طويلة."""
    for attempt in range(6):
        if attempt > 0:
            time.sleep(3)  # تأخير بسيط بين المحاولات لتفادي حد الطلبات بالدقيقة
        theme = random.choice(THEMES)
        style = random.choice(STYLES)
        style_examples = EXAMPLES_BY_STYLE[style]
        examples_text = "\n".join(f"- {ex}" for ex in style_examples)
        prompt = (
            "أنت شاعر عراقي/عربي تكتب لقناة تيليجرام مختصة بالشعر والخواطر المؤثرة.\n"
            f"أمثلة حقيقية بأسلوب {style} تحديداً (للإلهام فقط، لا تنسخها):\n"
            f"{examples_text}\n\n"
            f"اكتب نصاً عربياً جديداً تماماً عن موضوع: {theme}.\n"
            "المطلوب:\n"
            f"- اكتب النص بأسلوب {style} حصراً وبالكامل من أوله لآخره، بنفس روح الأمثلة أعلاه. "
            "ممنوع منعاً باتاً خلط الفصحى مع العامية بنفس النص.\n"
            "- ممنوع منعاً باتاً أي حرف أو كلمة إنجليزية.\n"
            "- يمكن أن يكون بيت شعر كامل بشطرين (صدر وعجز)، أو جملة نثرية، المهم أن يكون "
            "مكتملاً تماماً من أوله لآخره ولا يبدو منقوصاً أو متوقفاً في المنتصف.\n"
            "- بلاغة وقوة تعبير (تشبيه أو مفارقة أو حكمة).\n"
            "- بدون علامات تنصيص، وبدون كلمة 'خاطرة' أو 'قصيدة' أو 'جملة'.\n"
            "- بدون أي مقدمات أو تعليقات أو ترجمة.\n"
            "- أعطني النص العربي مباشرة بدون أي شيء آخر."
        )

        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 400,
        }
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        try:
            choice = data["choices"][0]
            text = choice["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"رد Groq غير متوقع: {data}") from e

        # لو النص انقطع بسبب حد الطول (مو لأنه خلص طبيعياً)، نتجاهله ونعيد المحاولة
        finish_reason = choice.get("finish_reason", "")
        if finish_reason not in ("stop", ""):
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
            ("GROQ_API_KEY", GROQ_API_KEY),
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
