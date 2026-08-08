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

IRAQI_EXAMPLES = [
    "سهرت الليالي لعيونك تاليها تسهر لعيون غيري؟",
    "من تكدر تحط عينك و تباوع على الشمس يلا حط عينك بعيني",
    "تفگة وبالَيَمن تقنعني ما مَسحوب؟ حَتى اطفال رضّع ساحبه أقسامك",
    "شگد صعب اظل اضحك وگلبي مكسور بيه",
    "اريدك تفهم اني تعبت اسولف وياك بالسكوت",
    "خافف عليه الفراگ لو كان يعرف شگد اشتاگله",
    "ما اريد شي منك غير تذكرني ولو بخاطرة وحدة",
    "الوگت يمر وياخذ الناس ويخلي بس الذكرى ورانا",
    "دايم اكول الصبر مفتاح الفرج لو صبرت شوي",
    "شلون انساك وانت اغلى شي مر بحياتي؟",
]

# كلمات لو انتهى بها النص غالباً معناها انقطع بالمنتصف (حرف عطف/جر)
_INCOMPLETE_ENDINGS = ("و", "أو", "في", "من", "على", "إلى", "عن", "مع", "لأن", "حتى", "لكن")

# رسائل جمعة مباركة (يُختار منها عشوائياً)
JUMUA_MESSAGES = [
    "جمعة مباركة على الجميع، تقبل الله منا ومنكم صالح الأعمال",
    "جمعة مباركة، جعلها الله يوم خير وبركة وسعادة على قلوبكم",
    "كل جمعة وأنتم بخير، جمعة مباركة أعادها الله عليكم باليمن والبركات",
    "جمعة مباركة، اللهم اجعل هذا اليوم بداية خير وسعادة لنا جميعاً",
]


def _has_decent_rhyme(text: str) -> bool:
    """لو النص أكثر من سطرين، يتحقق من وجود قافية متقاربة بين نهايات الأبيات."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 3:
        return True  # نص قصير، ما يحتاج تحقق قافية

    def rhyme_key(line: str) -> str:
        word = line.rstrip("؟!.،").split()[-1] if line.split() else ""
        return word[-2:] if len(word) >= 2 else word

    endings = [rhyme_key(l) for l in lines]
    # نحسب أكثر نهاية متكررة بين الأبيات
    from collections import Counter
    common_count = Counter(endings).most_common(1)[0][1] if endings else 0
    # نطلب على الأقل نص الأبيات تشترك بنفس نهاية القافية تقريباً
    return common_count >= max(2, len(lines) // 2)


def _is_valid_arabic(text: str) -> bool:
    """يتحقق أن كل حرف بالنص إما عربي أو مسافة أو علامة ترقيم أساسية، مكتمل، وما ينتهي بحرف عطف/جر."""
    allowed_punctuation = set("؟!.،-ـ()\n \t'\"")
    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in text)

    def is_allowed_char(ch: str) -> bool:
        if "\u0600" <= ch <= "\u06FF":  # عربي أساسي
            return True
        if "\u0750" <= ch <= "\u077F":  # ملحق عربي
            return True
        if "\uFB50" <= ch <= "\uFDFF" or "\uFE70" <= ch <= "\uFEFF":  # أشكال عرض عربية
            return True
        if ch.isdigit():
            return True
        if ch in allowed_punctuation:
            return True
        return False

    has_foreign_chars = any(not is_allowed_char(ch) for ch in text)
    looks_broken = "(" in text or ")" in text or len(text) < 8
    word_count = len(text.split())
    too_long = word_count > 150  # حماية فقط ضد النصوص المبالغ بطولها جداً
    last_line = text.strip().split("\n")[-1].strip()
    last_word = last_line.rstrip("؟!.،").split()[-1] if last_line.split() else ""
    ends_incomplete = last_word in _INCOMPLETE_ENDINGS
    return (
        has_arabic
        and not has_foreign_chars
        and not looks_broken
        and not too_long
        and not ends_incomplete
        and _has_decent_rhyme(text)
    )


def generate_quote() -> str:
    """يطلب من Groq نص باللهجة العراقية الأصيلة فقط، كامل ومترابط، بأسطر متعددة أو سطر واحد."""
    for attempt in range(6):
        if attempt > 0:
            time.sleep(3)  # تأخير بسيط بين المحاولات لتفادي حد الطلبات بالدقيقة
        theme = random.choice(THEMES)
        examples_text = "\n".join(f"- {ex}" for ex in random.sample(IRAQI_EXAMPLES, 5))
        prompt = (
            "أنت شاعر عراقي تكتب لقناة تيليجرام مختصة بالشعر والخواطر المؤثرة.\n"
            "أمثلة حقيقية باللهجة العراقية تحديداً (للإلهام بالروح والمفردات فقط، لا تنسخها):\n"
            f"{examples_text}\n\n"
            f"اكتب نصاً جديداً تماماً عن موضوع: {theme}.\n"
            "المطلوب:\n"
            "- اللهجة العراقية الأصيلة حصراً (مفردات وتراكيب عراقية واضحة مثل: "
            "تكدر، هَواي، شلون، اشتاگ، گلبي، اريدك، خافف، وياج، شگول). "
            "استخدم الحروف العراقية الخاصة بمكانها الصحيح: گ (بدل ك بصوت الجيم القاهرية) "
            "وچ (بدل چ بصوت التش) حسب النطق العراقي الصحيح للكلمة، وضع علامة الاستفهام ؟ "
            "بنهاية كل جملة استفهامية فعلياً.\n"
            "ممنوع منعاً باتاً اللهجة السعودية أو الخليجية أو الفصحى أو أي خلط بينهم.\n"
            "- ممنوع منعاً باتاً أي حرف أو كلمة إنجليزية.\n"
            "- استخدم فقط كلمات عراقية حقيقية ومتداولة فعلاً، ولا تخترع كلمات جديدة "
            "أو تشوّه كلمات موجودة. كل كلمة لازم تكون مفهومة وصحيحة إملائياً بالكامل.\n"
            "- يمكن أن يكون النص من سطر واحد قصير إلى قصيدة كاملة تصل حتى خمسة أبيات "
            "(كل بيت بسطر مستقل)، حسب ما يناسب الفكرة. "
            "المهم أن يكون مكتملاً تماماً من أوله لآخره ولا يبدو منقوصاً أو متوقفاً في المنتصف.\n"
            "- بلاغة وقوة تعبير (تشبيه أو مفارقة أو حكمة أو غزل).\n"
            "- ضع علامة استفهام (؟) بنهاية أي سطر يكون فعلياً سؤالاً أو استفهاماً "
            "(مثل الأسطر اللي تبدأ بـ 'شلون' أو 'وين' أو 'شگول' أو 'ليش' أو 'شگد'), "
            "ولا تنساها أبداً في هذي الحالة.\n"
            "- إذا كتبت أكثر من بيت، احرص على وجود قافية موحدة أو متقاربة في نهاية الأبيات "
            "لإعطاء إيقاع شعري واضح.\n"
            "- بدون علامات تنصيص، وبدون كلمة 'خاطرة' أو 'قصيدة' أو 'جملة'، وبدون إيموجي.\n"
            "- بدون أي مقدمات أو تعليقات أو ترجمة.\n"
            "- أعطني النص مباشرة بدون أي شيء آخر."
        )

        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 900,
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

    lines = [line for line in text.split("\n") if line.strip()]
    # لو النص أكثر من سطرين، نضيف فراغ بين كل بيتين لتحسين شكل العرض
    if len(lines) > 2:
        spaced_lines = []
        for i, line in enumerate(lines):
            spaced_lines.append(line)
            if i % 2 == 1 and i != len(lines) - 1:
                spaced_lines.append("")
        lines = spaced_lines
    quoted_lines = "\n".join(escape_html(line) for line in lines)
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
