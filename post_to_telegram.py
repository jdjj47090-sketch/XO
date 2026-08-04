#!/usr/bin/env python3
"""
بوت ينشر خواطر/أبيات قصيرة تلقائياً بقناة تيليجرام.
يقرأ الإعدادات من متغيرات البيئة (Environment Variables):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHANNEL   (مثال: @mahdi09245)
  GEMINI_API_KEY
"""

import os
import sys
import random
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent?key=" + str(GEMINI_API_KEY)
)

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


def generate_quote() -> str:
    """يطلب من Gemini نص عربي (فصيح أو عراقي) كامل ومترابط، بدون حد أقصى للطول."""
    for attempt in range(5):
        theme = random.choice(THEMES)
        examples_text = "\n".join(f"- {ex}" for ex in EXAMPLES)
        prompt = (
            "أنت شاعر عراقي/عربي تكتب لقناة تيليجرام مختصة بالشعر والخواطر المؤثرة.\n"
            "أمثلة حقيقية من أسلوب القناة (للإلهام فقط، لا تنسخها):\n"
            f"{examples_text}\n\n"
            f"اكتب نصاً عربياً جديداً تماماً عن موضوع: {theme}.\n"
            "المطلوب:\n"
            "- اللغة عربية فصحى أو باللهجة العراقية فقط، ممنوع منعاً باتاً أي حرف أو كلمة إنجليزية.\n"
            "- نص واحد، مكتمل المعنى ومترابط تماماً من أوله لآخره، لا ينتهي بشكل مفاجئ أو ناقص.\n"
            "- يمكن أن يكون بيت شعر طويل إذا احتاج الموضوع ذلك، لا يوجد حد أقصى للطول، المهم اكتمال المعنى.\n"
            "- بلاغة وقوة تعبير (تشبيه أو مفارقة أو حكمة).\n"
            "- بدون علامات تنصيص، وبدون كلمة 'خاطرة' أو 'قصيدة' أو 'جملة'.\n"
            "- بدون أي مقدمات أو تعليقات أو ترجمة.\n"
            "- أعطني النص العربي مباشرة بدون أي شيء آخر."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 400,
            },
        }

        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"رد Gemini غير متوقع: {data}") from e

        # تنظيف أي علامات اقتباس أو تنصيص زايدة
        text = text.strip('"').strip("«»").strip()

        # تحقق: النص عربي بالكامل تقريباً (بدون أي حرف إنجليزي)، وطوله معقول
        has_english = any(("a" <= ch.lower() <= "z") for ch in text)
        has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)
        looks_broken = "(" in text or ")" in text or len(text) < 8
        if has_arabic and not has_english and not looks_broken:
            return text

    # لو فشلت كل المحاولات، استخدم نص احتياطي بسيط
    return "الأيام تمضي وتبقى الذكرى وحدها شاهدة على ما كان"


def post_to_telegram(text: str) -> None:
    """ينشر النص بالقناة على شكل اقتباس (blockquote)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # نغلف النص بـ blockquote عشان يطلع بنفس شكل قناتك (الخط الجانبي + علامات التنصيص)
    html_text = f"<blockquote>&#8220;{escape_html(text)}&#8221;</blockquote>"

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
        quote = generate_quote()
        post_to_telegram(quote)
    except Exception as e:
        print("خطأ:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
