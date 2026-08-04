GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key=" + str(GEMINI_API_KEY)
)


def generate_quote() -> str:
    """يطلب من Gemini قصيدة أو أبيات شعرية كاملة مع معالجة خطأ 429."""
    for attempt in range(6):
        if attempt > 0:
            time.sleep(5)  # انتظار بين المحاولات

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
            "7. أعطني الأبيات الشعرية مباشرة بدون أي مقدمات أو شرح وبدون علامات تنصيص."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.85,
                "maxOutputTokens": 700,
            },
        }

        try:
            resp = requests.post(GEMINI_URL, json=payload, timeout=30)

            # إذا وصل حد الطلبات (429)، ننتظر ونجرب مرة ثانية
            if resp.status_code == 429:
                print("تجاوز حد الطلبات (429)، جاري الانتظار 10 ثوانٍ...")
                time.sleep(10)
                continue

            resp.raise_for_status()
            data = resp.json()

            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            text = text.strip('"').strip("«»").strip()

            if _is_valid_arabic(text):
                return text

        except Exception as e:
            print(f"محاولة {attempt + 1} فشلت: {e}")
            time.sleep(3)

    # نص احتياطي في حال فشل التوليد تماماً
    return (
        "رَفَعتُ نَفسي عَن هَوانِ وِدادِكُم\n"
        "فَالجَبلُ لا يَهوي لِغيرِ ذُراهُ\n"
        "وَتَرَكتُ ما بَينِي وَبَينَكُمُ الهَوى\n"
        "عِزّاً لِنَفسِي كَي يَعُودَ صَداهُ"
    )
