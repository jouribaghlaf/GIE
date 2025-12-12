# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple

# اختياري: لو موجود OpenAI SDK يشتغل، لو مو موجود يروح fallback
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore


SEGMENT_INDIVIDUAL = "individual"


_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"\d")


def is_valid_arabic_query(text: str) -> bool:
    """
    نرفض:
    - نص إنجليزي/رموز/عشوائي
    - نص قصير جدًا
    - نص ما فيه أي حروف عربية
    - جمل غير مرتبطة بخدمات حكومية (فلترة بسيطة)
    """
    t = (text or "").strip()
    if len(t) < 4:
        return False

    # لازم فيه عربي
    if not _ARABIC_RE.search(t):
        return False

    # لو أغلبه لاتيني/رموز
    latin = len(_LATIN_RE.findall(t))
    arab = len(_ARABIC_RE.findall(t))
    if latin > 0 and arab < 3:
        return False

    # كلمات “حياتية” مو خدمات (فلترة خفيفة)
    bad_phrases = [
        "اتروش", "استحم", "شاور", "اكل", "أنام", "انام", "العب", "افطر", "غداء", "عشاء",
        "ابا اروح", "ابي اروح"
    ]
    low = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").lower()
    for bp in bad_phrases:
        if bp in low:
            return False

    # لازم فيه “نية/فعل” قريب من خدمات
    good_hints = [
        "ابغى", "ابي", "أبي", "ابا", "أبغى", "احتاج", "أحتاج", "كيف", "اصدار", "إصدار",
        "تجديد", "حجز", "موعد", "بلاغ", "تأشيرة", "تفويض", "وثيقة", "سداد", "مدفوعات",
        "اقامة", "جواز", "هوية", "رخصة", "نقل", "مخالفات", "سفر"
    ]
    if not any(h.replace("أ", "ا").lower() in low for h in good_hints):
        # مثال: “ودي اسافر” نسمح له
        if "اسافر" not in low and "سافر" not in low:
            return False

    return True


def _get_openai_client() -> Optional[Any]:
    if OpenAI is None:
        return None
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)


# ---------- كتالوج نوايا (أفراد) ----------
INTENTS: Dict[str, Dict[str, Any]] = {
    "travel": {
        "label_ar": "السفر والتنقل",
        "keywords": ["سفر", "اسافر", "رحلة", "تذكرة", "مطار", "خروج وعودة", "تاشيرة", "تأشيرة"],
    },
    "appointments": {
        "label_ar": "إدارة المواعيد",
        "keywords": ["موعد", "مواعيد", "حجز", "حجز موعد", "الغاء موعد", "تعديل موعد"],
    },
    "payments": {
        "label_ar": "المدفوعات الحكومية",
        "keywords": ["سداد", "مدفوعات", "رسوم", "فاتورة", "سدد", "اسدد"],
    },
    "delegation": {
        "label_ar": "إدارة التفويض",
        "keywords": ["تفويض", "تفويض شخص", "تفويض ابشر", "تفويض مركبة", "تفويض قيادة"],
    },
    "documents_delivery": {
        "label_ar": "توصيل الوثائق",
        "keywords": ["توصيل", "وثائق", "عنوان وطني", "توصيل الوثيقة", "استلام الوثائق"],
    },
    "personal_docs": {
        "label_ar": "الوثائق الشخصية",
        "keywords": ["هوية", "جواز", "رخصة", "تجديد الهوية", "تجديد الجواز", "انتهاء الرخصة"],
    },
    "fraud_report": {
        "label_ar": "البلاغات والاحتيال",
        "keywords": ["احتيال", "نصب", "ابتزاز", "اختراق", "بلاغ", "جرائم الانترنت"],
    },
}


# ---------- خدمات (Objects) ----------
# NOTE: action هنا “محاكاة انتقال” — تقدرين تغيرين target لأي مسار تبغينه
SERVICE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "travel": [
        {
            "id": "passport_check",
            "title": "التحقق من صلاحية الجواز",
            "description": "التحقق من صلاحية جواز السفر للمستفيد والمرافقين.",
            "action": {"type": "navigate", "target": "passport-check"},
        },
        {
            "id": "travel_permit",
            "title": "إصدار تصريح سفر",
            "description": "تقديم طلب تصريح سفر إلكتروني (محاكاة).",
            "action": {"type": "navigate", "target": "travel-permit"},
        },
        {
            "id": "visa_services",
            "title": "خدمات التأشيرات",
            "description": "اقتراح المسار المناسب للتأشيرة حسب الحالة (محاكاة).",
            "action": {"type": "navigate", "target": "visa"},
        },
        {
            "id": "violations_check",
            "title": "التحقق من المخالفات قبل السفر",
            "description": "التأكد من عدم وجود التزامات/مخالفات تعيق السفر (محاكاة).",
            "action": {"type": "navigate", "target": "violations"},
        },
    ],
    "appointments": [
        {
            "id": "manage_appointments",
            "title": "إدارة المواعيد",
            "description": "حجز/تعديل/إلغاء موعد (محاكاة).",
            "action": {"type": "navigate", "target": "appointments"},
        }
    ],
    "payments": [
        {
            "id": "gov_payments",
            "title": "المدفوعات الحكومية",
            "description": "سداد الرسوم الحكومية عبر القنوات المتاحة (محاكاة).",
            "action": {"type": "navigate", "target": "payments"},
        }
    ],
    "delegation": [
        {
            "id": "manage_delegation",
            "title": "إدارة التفويض",
            "description": "إنشاء/إلغاء تفويض (محاكاة).",
            "action": {"type": "navigate", "target": "delegation"},
        }
    ],
    "documents_delivery": [
        {
            "id": "documents_delivery",
            "title": "توصيل الوثائق",
            "description": "طلب توصيل الوثائق لعنوانك الوطني (محاكاة).",
            "action": {"type": "navigate", "target": "documents-delivery"},
        }
    ],
    "personal_docs": [
        {
            "id": "renew_id",
            "title": "تجديد الهوية الوطنية",
            "description": "متطلبات وخطوات التجديد (محاكاة).",
            "action": {"type": "navigate", "target": "renew-id"},
        },
        {
            "id": "renew_passport",
            "title": "تجديد جواز السفر",
            "description": "خطوات التجديد والرسوم (محاكاة).",
            "action": {"type": "navigate", "target": "renew-passport"},
        },
    ],
    "fraud_report": [
        {
            "id": "fraud_report",
            "title": "رفع بلاغ احتيال",
            "description": "اختيار نوع البلاغ وتجهيز البيانات (محاكاة).",
            "action": {"type": "navigate", "target": "fraud-report"},
        }
    ],
}


def _keyword_scores(text: str) -> List[Tuple[str, float]]:
    t = text.strip()
    scored: List[Tuple[str, float]] = []
    for intent_id, meta in INTENTS.items():
        score = 0
        for kw in meta.get("keywords", []):
            if kw in t:
                score += 1
        if score > 0:
            scored.append((intent_id, float(score)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _intent_label(intent_id: str) -> str:
    return INTENTS.get(intent_id, {}).get("label_ar", intent_id)


def classify_with_openai(user_text: str, top_k: int = 3, model: str = "gpt-4o-mini") -> List[Dict[str, Any]]:
    client = _get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI client not available.")

    catalog = [{"id": k, "label_ar": v["label_ar"]} for k, v in INTENTS.items()]

    system = (
        "أنت مصنّف نوايا عربي لخدمات حكومية رقمية. "
        "اختر أقرب نية من قائمة ثابتة. أخرج JSON فقط."
    )
    user = {
        "text": user_text,
        "intents_catalog": catalog,
        "required_output": {
            "top_intents": [{"id": "intent_id", "confidence": 0.0, "reason_ar": "سبب قصير"}]
        },
        "rules": [
            "اختر فقط من intent IDs الموجودة في القائمة.",
            f"أعد {top_k} نتائج كحد أقصى مرتبة من الأعلى للأقل.",
            "confidence رقم بين 0 و 1.",
        ],
    }

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.2,
        max_output_tokens=300,
    )

    content = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    content += c.text
    content = content.strip()

    # Handle fenced code blocks لو صار ```json
    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()

    data = json.loads(content)
    top_intents = data.get("top_intents", [])

    allowed = set(INTENTS.keys())
    out: List[Dict[str, Any]] = []
    for it in top_intents:
        iid = it.get("id")
        if iid in allowed:
            out.append({
                "id": iid,
                "label_ar": _intent_label(iid),
                "confidence": float(it.get("confidence", 0.0)),
                "reason_ar": str(it.get("reason_ar", ""))[:120],
            })
    return out[:top_k]


def services_for(intent_id: Optional[str]) -> List[Dict[str, Any]]:
    if not intent_id:
        return []
    return SERVICE_CATALOG.get(intent_id, [])


def gie_engine(segment: str, user_text: str) -> Dict[str, Any]:
    segment = (segment or "").strip().lower()
    text = (user_text or "").strip()

    if segment != SEGMENT_INDIVIDUAL:
        segment = SEGMENT_INDIVIDUAL

    if not is_valid_arabic_query(text):
        return {
            "mode": "invalid",
            "segment": segment,
            "input_text": text,
            "detected_intent": None,
            "confidence": 0.0,
            "top_intents": [],
            "services": [],
            "service_bundle": [],
        }

    # 1) OpenAI
    try:
        top = classify_with_openai(text, top_k=3)
        best = top[0]["id"] if top else None
        conf = float(top[0]["confidence"]) if top else 0.0
        services = services_for(best)

        return {
            "mode": "openai",
            "segment": segment,
            "input_text": text,
            "detected_intent": best,
            "confidence": conf,
            "top_intents": top,
            "services": services,
            # للنسخ القديمة: list نصية
            "service_bundle": [s.get("title", "") for s in services],
        }

    except Exception as e:
        # 2) fallback keywords
        scored = _keyword_scores(text)
        top2 = []
        for iid, score in scored[:3]:
            conf = min(0.85, 0.30 + 0.15 * score)
            top2.append({
                "id": iid,
                "label_ar": _intent_label(iid),
                "confidence": conf,
                "reason_ar": "تطابق كلمات مفتاحية"
            })

        best = top2[0]["id"] if top2 else None
        conf_best = float(top2[0]["confidence"]) if top2 else 0.0
        services = services_for(best)

        return {
            "mode": "fallback",
            "fallback_reason": str(e),
            "segment": segment,
            "input_text": text,
            "detected_intent": best,
            "confidence": conf_best,
            "top_intents": top2,
            "services": services,
            "service_bundle": [s.get("title", "") for s in services],
        }
