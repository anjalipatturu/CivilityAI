"""Deterministic, keyword-based content moderation for Civility.ai.

Text moderation is fully keyword-based. Image/video functions still rely on
Gemini if configured, otherwise fall back to a simple demo response.
"""

import json
import re

from django.conf import settings

_genai = None
_genai_import_error = None


# Prefer widely available, stable model IDs by default for non-text content.
TEXT_MODEL_ID = getattr(settings, 'GEMINI_TEXT_MODEL_ID', 'gemini-1.5-flash')
VISION_MODEL_ID = getattr(settings, 'GEMINI_VISION_MODEL_ID', 'gemini-1.5-flash')


def _ensure_genai_loaded():
    """Lazy-load google.generativeai and cache import state."""
    global _genai, _genai_import_error
    if _genai is not None or _genai_import_error is not None:
        return _genai

    try:
        import google.generativeai as genai
        _genai = genai
    except Exception as exc:
        _genai_import_error = str(exc)
        _genai = None
    return _genai


def configure_gemini():
    """Configure the Gemini API with the API key.

    Returns the API key string (or empty string if not configured).
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return ''

    genai = _ensure_genai_loaded()
    if not genai:
        return ''

    try:
        genai.configure(api_key=api_key)
    except Exception:
        return ''
    return api_key


def _map_civility_json_to_internal(content_type, civility_obj):
    """Map Civility.ai SAFE/UNSAFE JSON to internal moderation format.

    civility_obj schema (for image/video):
    {
      "status": "SAFE" | "UNSAFE",
      "category": str,
      "severity": "low" | "medium" | "high",
      "confidence": "0-100",
      "reason": str,
    }
    """
    try:
        status_raw = (civility_obj.get('status') or '').upper()
        status = 'Approved' if status_raw == 'SAFE' else 'Flagged'

        category = civility_obj.get('category') or 'safe'
        if category == 'safe':
            categories = []
        else:
            categories = [category]

        severity = (civility_obj.get('severity') or '').lower()
        if severity == 'low':
            abusive_score = 20
        elif severity == 'medium':
            abusive_score = 55
        elif severity == 'high':
            abusive_score = 85
        else:
            abusive_score = 0

        try:
            confidence_val = int(str(civility_obj.get('confidence', '80')).strip())
        except (TypeError, ValueError):
            confidence_val = 80

        confidence_val = max(0, min(100, confidence_val))

        reason = civility_obj.get('reason') or 'No issues detected'
    except Exception:
        # Fallback to safe defaults if mapping fails
        status = 'Approved'
        categories = []
        abusive_score = 0
        confidence_val = 80
        reason = 'No issues detected'

    return {
        'content_type': content_type,
        'status': status,
        'reason': reason,
        'confidence_score': confidence_val,
        'abusive_score': abusive_score,
        'categories_detected': categories,
        'corrected_text': None,
    }


def _keyword_moderation(text, content_type='text'):
    """Score text deterministically based on abusive / harmful keywords.

    Returns a dict with: status, reason, confidence_score, abusive_score,
    categories_detected, corrected_text.
    """
    if not isinstance(text, str):
        text = ''

    lowered = text.lower()

    # Keyword buckets
    severe = [
        'kill', 'murder', 'bomb', 'terrorist', 'rape', 'lynch',
        'shoot you', 'i will kill', 'die you', 'suicide', 'self-harm',
    ]
    moderate = [
        'hate you', 'hate them', 'attack', 'threat', 'beat you',
        'go die', 'piece of trash',
    ]
    mild = [
        'stupid', 'idiot', 'dumb', 'loser', 'ugly', 'shut up',
        'damn', 'hell',
    ]

    profanity = [
        'fuck', 'shit', 'bitch', 'bastard',
    ]

    found_severe = [kw for kw in severe if kw in lowered]
    found_moderate = [kw for kw in moderate if kw in lowered]
    found_mild = [kw for kw in mild if kw in lowered]
    found_profanity = [kw for kw in profanity if kw in lowered]

    total_severe = len(found_severe)
    total_moderate = len(found_moderate)
    total_mild = len(found_mild)
    total_profanity = len(found_profanity)

    # Determine severity bucket so scores fall cleanly into
    # 0–25, 26–50, 51–75, 76–100 ranges.
    score = 0
    if total_severe:
        # Severe abuse → always in 76–100
        score = 80 + 3 * (total_severe - 1)
    elif total_moderate:
        # Moderate abuse → in 51–75
        score = 60 + 3 * (total_moderate - 1)
    elif (total_mild + total_profanity) > 0:
        # Mild warning → in 26–50
        base = 30
        extra = 2 * ((total_mild + total_profanity) - 1)
        score = base + extra

    # Cap score within 0–100
    score = max(0, min(100, score))

    if score == 0:
        status = 'Approved'
        reason = 'Content appears safe and respectful.'
        categories = []
    else:
        status = 'Flagged'
        categories = []
        if total_severe:
            categories.append('Severe violence / threats')
        if total_moderate:
            categories.append('Harassment / bullying')
        if total_mild or total_profanity:
            categories.append('Profanity / insulting language')

        reason_parts = []
        if found_severe or found_moderate or found_mild or found_profanity:
            all_found = found_severe + found_moderate + found_mild + found_profanity
            reason_parts.append(
                'Content contains potentially harmful or abusive language: '
                + ', '.join(sorted(set(all_found)))
            )
        else:
            reason_parts.append('Content appears borderline abusive or inappropriate.')
        reason = ' '.join(reason_parts)

    # Confidence is high because this is deterministic
    confidence = 100 if score == 0 else 95

    # Safe rewrite: replace harmful words with polite / neutral phrases
    corrected = text
    if score > 0:
        replacements = {
            # severe
            'kill': 'harm',
            'murder': 'seriously hurt',
            'bomb': 'damage',
            'terrorist': 'dangerous person',
            'rape': 'assault',
            'lynch': 'attack',
            'shoot you': 'threaten you',
            'i will kill': 'I will seriously upset',
            'die you': 'leave you alone',
            'suicide': 'self-harm',
            'self-harm': 'hurt myself',
            # moderate
            'hate you': "strongly dislike you",
            'hate them': "strongly dislike them",
            'attack': 'criticize',
            'threat': 'warning',
            'beat you': 'defeat you',
            'go die': 'go away',
            'piece of trash': 'unpleasant person',
            # mild / insults / profanity
            'stupid': 'unwise',
            'idiot': 'person',
            'dumb': 'unkind',
            'loser': 'person',
            'ugly': 'unattractive',
            'shut up': 'be quiet',
            'damn': 'very',
            'hell': 'really',
            'fuck': 'mess',
            'shit': 'problem',
            'bitch': 'person',
            'bastard': 'person',
        }

        try:
            # Replace longer phrases first to avoid partial overlaps
            for kw in sorted(replacements.keys(), key=len, reverse=True):
                corrected = re.sub(kw, replacements[kw], corrected, flags=re.IGNORECASE)
        except Exception:
            corrected = 'This content has been rewritten to be more respectful.'

    return {
        'content_type': content_type,
        'status': status,
        'reason': reason,
        'confidence_score': confidence,
        'abusive_score': score,
        'categories_detected': categories,
        'corrected_text': corrected if score > 0 else None,
    }


def analyze_text_content(text, content_type='text'):
    """Main entry for text moderation: purely keyword-based and deterministic."""
    return _keyword_moderation(text, content_type)


def analyze_image_content(image_path, content_type='image'):
    """Analyze image content using Gemini Vision."""
    api_key = configure_gemini()

    if not api_key:
        return _demo_moderation_response('Image content', content_type)

    try:
        import PIL.Image
        # Use multimodal/vision-capable model
        model = genai.GenerativeModel(VISION_MODEL_ID)
        image = PIL.Image.open(image_path)

        # Civility.ai image moderation prompt using SAFE/UNSAFE JSON schema
        prompt = """
You are an AI image moderation engine for Civility.ai.

Analyze this image carefully.

Detect:
- Nudity
- Violence
- Weapons
- Blood or injury
- Hate symbols
- Offensive gestures
- Drugs or harmful activity
- Sexual content
- Unsafe public content

Instructions:
- Consider full scene context.
- Ignore harmless artistic or educational content.
- Detect hidden harmful intent.

Return ONLY valid JSON:

{
  "status": "SAFE or UNSAFE",
  "category": "nudity / violence / weapon / hate / drugs / sexual / safe",
  "severity": "low / medium / high",
  "confidence": "0-100",
  "reason": "short explanation"
}
"""

        response = model.generate_content([prompt, image])
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

        civility_result = json.loads(response_text)
        return _map_civility_json_to_internal(content_type, civility_result)
    except Exception as e:
        return _demo_moderation_response('Image content', content_type, error=str(e))


def analyze_video_content(video_path, content_type='video'):
    """Analyze video content - extracts key info and sends to Gemini."""
    api_key = configure_gemini()

    if not api_key:
        return _demo_moderation_response('Video content', content_type)

    try:
        # Use multimodal/vision-capable model
        model = genai.GenerativeModel(VISION_MODEL_ID)

        # Upload video file for Gemini analysis
        video_file = genai.upload_file(path=video_path)

        # Civility.ai video moderation prompt using SAFE/UNSAFE JSON schema
        prompt = """
You are an AI video moderation engine for Civility.ai.

Analyze these extracted video frames carefully.

Detect:
- Violence
- Nudity
- Abuse
- Weapons
- Harmful acts
- Sexual content
- Dangerous behavior

Instructions:
- Evaluate sequence across frames.
- Detect repeated harmful actions.
- Ignore harmless motion.

Return ONLY valid JSON:

{
  "status": "SAFE or UNSAFE",
  "category": "violence / nudity / weapon / abuse / dangerous / safe",
  "severity": "low / medium / high",
  "confidence": "0-100",
  "reason": "short explanation"
}
"""

        response = model.generate_content([prompt, video_file])
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

        civility_result = json.loads(response_text)
        return _map_civility_json_to_internal(content_type, civility_result)
    except Exception as e:
        return _demo_moderation_response('Video content', content_type, error=str(e))


def _demo_moderation_response(content, content_type, error=None):
    """Generate a demo moderation response for testing without API key."""
    # Simple keyword-based detection for demo
    flagged_keywords = [
        'kill', 'hate', 'die', 'stupid', 'idiot', 'damn', 'hell',
        'violence', 'attack', 'bomb', 'threat', 'abuse', 'harass',
    ]

    content_lower = content.lower() if isinstance(content, str) else ''
    found = [kw for kw in flagged_keywords if kw in content_lower]

    if found:
        # Very simple sanitization: mask flagged keywords to produce a
        # less harmful version of the original text.
        sanitized = content
        try:
            for kw in found:
                sanitized = re.sub(kw, '*' * len(kw), sanitized, flags=re.IGNORECASE)
        except Exception:
            sanitized = 'This content has been flagged. Please rephrase your message in a respectful manner.'

        return {
            'content_type': content_type,
            'status': 'Flagged',
            'reason': f'Content contains potentially harmful language: {", ".join(found)}',
            'confidence_score': 90,
            'abusive_score': 85,
            'categories_detected': ['Profanity', 'Potential harassment'],
            'corrected_text': sanitized,
        }

    return {
        'content_type': content_type,
        'status': 'Approved',
        'reason': 'Content appears safe and appropriate.',
        'confidence_score': 100,
        'abusive_score': 0,
        'categories_detected': [],
        'corrected_text': None,
    }
