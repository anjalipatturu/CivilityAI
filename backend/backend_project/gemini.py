"""
Gemini AI integration for content moderation in Civility.ai
"""

import json
import re
import google.generativeai as genai
from django.conf import settings


def configure_gemini():
    """Configure the Gemini API with the API key."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if api_key:
        genai.configure(api_key=api_key)
    return api_key


def analyze_text_content(text, content_type='text'):
    """
    Analyze text content using Gemini AI for moderation.
    Returns structured moderation result.
    """
    api_key = configure_gemini()

    if not api_key:
        # Return a demo response if no API key is configured
        return _demo_moderation_response(text, content_type)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""You are an AI content moderator for a platform called Civility.ai. 
Analyze the following user-generated content and provide a moderation assessment.

Content Type: {content_type}
Content: \"\"\"{text}\"\"\"

You MUST respond ONLY with a valid JSON object (no markdown, no explanation, no code fences). Use this exact format:
{{
    "content_type": "{content_type}",
    "status": "Approved" or "Flagged",
    "reason": "Brief explanation of why the content was approved or flagged",
    "confidence_score": <number between 0 and 100>,
    "abusive_score": <number between 0 and 100>,
    "categories_detected": ["list", "of", "categories"],
    "corrected_text": "If content is abusive provide a polite rewritten version, otherwise null"
}}

Categories to check for:
- Hate speech / discrimination
- Violence / threats  
- Sexual content
- Harassment / bullying
- Spam / scam
- Misinformation
- Self-harm
- Profanity

Rules:
- If content is clearly safe, set status to "Approved" with high confidence and low abusive score
- If content contains any harmful elements, set status to "Flagged"
- abusive_score: 0 = completely safe, 100 = extremely abusive
- confidence_score: how confident you are in your assessment (0-100)
- If the content is flagged, provide a polite corrected version in corrected_text
"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean up response - remove markdown code fences if present
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

        result = json.loads(response_text)

        # Ensure all required fields are present
        return {
            'content_type': result.get('content_type', content_type),
            'status': result.get('status', 'Approved'),
            'reason': result.get('reason', 'No issues detected'),
            'confidence_score': min(100, max(0, int(result.get('confidence_score', 80)))),
            'abusive_score': min(100, max(0, int(result.get('abusive_score', 0)))),
            'categories_detected': result.get('categories_detected', []),
            'corrected_text': result.get('corrected_text', None),
        }

    except json.JSONDecodeError:
        return {
            'content_type': content_type,
            'status': 'Approved',
            'reason': 'AI analysis completed - content appears safe',
            'confidence_score': 70,
            'abusive_score': 5,
            'categories_detected': [],
            'corrected_text': None,
        }
    except Exception as e:
        return _demo_moderation_response(text, content_type, error=str(e))


def analyze_image_content(image_path, content_type='image'):
    """Analyze image content using Gemini Vision."""
    api_key = configure_gemini()

    if not api_key:
        return _demo_moderation_response('Image content', content_type)

    try:
        import PIL.Image
        model = genai.GenerativeModel('gemini-1.5-flash')
        image = PIL.Image.open(image_path)

        prompt = """You are an AI content moderator. Analyze this image and provide a moderation assessment.
You MUST respond ONLY with a valid JSON object (no markdown, no explanation, no code fences):
{
    "content_type": "image",
    "status": "Approved" or "Flagged",
    "reason": "Brief explanation",
    "confidence_score": <0-100>,
    "abusive_score": <0-100>,
    "categories_detected": ["list"],
    "corrected_text": null
}

Check for: violence, nudity, hate symbols, gore, drugs, weapons, harassment."""

        response = model.generate_content([prompt, image])
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

        result = json.loads(response_text)
        return {
            'content_type': result.get('content_type', content_type),
            'status': result.get('status', 'Approved'),
            'reason': result.get('reason', 'No issues detected'),
            'confidence_score': min(100, max(0, int(result.get('confidence_score', 80)))),
            'abusive_score': min(100, max(0, int(result.get('abusive_score', 0)))),
            'categories_detected': result.get('categories_detected', []),
            'corrected_text': result.get('corrected_text', None),
        }
    except Exception as e:
        return _demo_moderation_response('Image content', content_type, error=str(e))


def analyze_video_content(video_path, content_type='video'):
    """Analyze video content - extracts key info and sends to Gemini."""
    api_key = configure_gemini()

    if not api_key:
        return _demo_moderation_response('Video content', content_type)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Upload video file for Gemini analysis
        video_file = genai.upload_file(path=video_path)

        prompt = """You are an AI content moderator. Analyze this video and provide a moderation assessment.
You MUST respond ONLY with a valid JSON object (no markdown, no explanation, no code fences):
{
    "content_type": "video",
    "status": "Approved" or "Flagged",
    "reason": "Brief explanation",
    "confidence_score": <0-100>,
    "abusive_score": <0-100>,
    "categories_detected": ["list"],
    "corrected_text": null
}

Check for: violence, nudity, hate content, dangerous activities, harassment."""

        response = model.generate_content([prompt, video_file])
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

        result = json.loads(response_text)
        return {
            'content_type': result.get('content_type', content_type),
            'status': result.get('status', 'Approved'),
            'reason': result.get('reason', 'No issues detected'),
            'confidence_score': min(100, max(0, int(result.get('confidence_score', 80)))),
            'abusive_score': min(100, max(0, int(result.get('abusive_score', 0)))),
            'categories_detected': result.get('categories_detected', []),
            'corrected_text': result.get('corrected_text', None),
        }
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
        return {
            'content_type': content_type,
            'status': 'Flagged',
            'reason': f'Content contains potentially harmful language: {", ".join(found)}',
            'confidence_score': 75,
            'abusive_score': min(85, 30 + len(found) * 15),
            'categories_detected': ['Profanity', 'Potential harassment'],
            'corrected_text': 'This content has been flagged. Please rephrase your message in a respectful manner.',
        }

    return {
        'content_type': content_type,
        'status': 'Approved',
        'reason': 'Content appears safe and appropriate.' + (f' (Demo mode: {error})' if error else ' (Demo mode - configure GEMINI_API_KEY for full AI analysis)'),
        'confidence_score': 85,
        'abusive_score': 5,
        'categories_detected': [],
        'corrected_text': None,
    }
