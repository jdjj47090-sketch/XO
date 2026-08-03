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

# التعديل هنا: استخدام الإصدار v1 الصحيح مع الموديل
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)

# مواضيع مختلفة لتنويع المحتوى
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

# أمثلة بليغة ومكتملة المعنى ليتعلم منها النموذج النمط المطلوب
EXAMPLES = [
    "سَهِرْتُ لِأَجْلِكَ دَهْراً، فَهَلْ كَانَ جَزَائِي أَنْ تَسْهَرَ لِغَيْرِي؟",
    "أَحْسَنْتُ لَهُمْ دَهْراً وَأَسَأْتُ يَوْماً، فَنَسُوا الدَّهْرَ وَتَذَكَّرُوا الْيَوْمَ!",
    "وَمَا فَائِدةُ الدُّمُوعِ إِنْ كَانَتِ الأَقْدَارُ قَدْ كُتِبَتْ؟",
    "كَيْفَ لِعَيْنٍ أَلِفَتِ الشَّمْسَ أَنْ تُكْحَلَ بِالظَّلَامِ؟",
    "لَا شَيْءَ يَدُومُ لِلْأَبَدِ، حَتَّى الأَلَمُ يَمْضِي.",
]


def generate_quote() -> str:
    """يطلب من Gemini نص قصير مكتمل ومترابط وبليغ."""
    theme = random.choice(THEMES)
    examples_text = "\n".join(f"- {ex}" for ex in EXAMPLES)
    
    prompt = (
        "أنت أديب وكاتب خواطر وأبيات شعرية عربية فصيحة وقوية التأثير، تكتب لقناة تيليجرام.\n\n"
        "هذه أمثلة حقيقية لنمط وأسلوب الجمل المطلوبة (لا تكررها، افهم منها الأسلوب والبلاغة فقط):\n"
        f"{examples_text}\n\n"
        f"المطلوب: اكتب جملة واحدة جديدة تماماً عن موضوع: ({theme}).\n\n"
        "الشروط الصارمة:\n"
        "- اكتب جملة واحدة فقط تكون مكتملة المعنى ومترابطة نحوياً ولغوياً، ولا تنتهي بشكل ناقص أو مبتور.\n"
        "- استخدم لغة عربية فصيحة وبليغة (تشبيه، مفارقة، أو حكمة مركزة).\n"
        "- لا تزد عن 15 إلى 20 كلمة.\n"
        "- لا تستخدم علامات تنصيص ولا تضف كلمات مثل 'خاطرة' أو 'قصيدة'.\n"
        "- يمنع كتابة أي شرح أو تعليق أو مقدمات، اكتب النص فقط."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": 150,
        },
    }

    resp = requests.post(GEMINI_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"رد Gemini غير متوقع: {data}") from e

    # تنظيف شامل لأي علامات تنصيص زائدة
    text = text.strip('"\'«»”“').strip()
    return text


def escape_html(text: str) -> str:
    """هروب الحروف الخاصة بـ HTML لتجنب مشاكل التنسيق بفي تيليجرام."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def post_to_telegram(text: str) -> None:
    """ينشر النص بالقناة على شكل اقتباس (blockquote)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

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
