"""
API Views for Civility.ai backend
"""

import json
import os
import traceback
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import login_with_google, get_user_from_request
from .gemini import analyze_text_content, analyze_image_content, analyze_video_content
from .voice import convert_audio_to_text, save_uploaded_audio, cleanup_audio_file
from .mongo import save_moderation_log, get_user_moderation_logs
from .behavior import track_content_submission, get_behavior_summary, should_send_alert
from .utils import save_uploaded_file, cleanup_file, get_content_type_from_file, send_admin_alert
from .models import moderation_log_document


# ── Health Check ─────────────────────────────────────────────

def health_check(request):
    """API health check endpoint."""
    return JsonResponse({
        'status': 'ok',
        'service': 'Civility.ai API',
        'version': '1.0.0',
    })


# ── Authentication ───────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def google_login(request):
    """
    POST /auth/google-login
    Accept Google OAuth token, verify, create/update user, return JWT.
    """
    try:
        body = json.loads(request.body)
        google_token = body.get('token', '')

        if not google_token:
            return JsonResponse({
                'error': 'Google token is required'
            }, status=400)

        result, error = login_with_google(google_token)

        if error:
            return JsonResponse({
                'error': error
            }, status=401)

        return JsonResponse({
            'success': True,
            'token': result['token'],
            'user': result['user'],
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def verify_token(request):
    """
    GET /auth/verify
    Verify the JWT token from Authorization header.
    """
    user_id = get_user_from_request(request)

    if not user_id:
        return JsonResponse({'error': 'Invalid or expired token'}, status=401)

    from .mongo import find_user_by_id
    user = find_user_by_id(user_id)

    if user:
        return JsonResponse({
            'valid': True,
            'user': {
                'user_id': user.get('user_id'),
                'email': user.get('email'),
                'name': user.get('name', ''),
                'picture': user.get('picture', ''),
            }
        })

    return JsonResponse({'valid': True, 'user_id': user_id})


# ── Content Moderation ───────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def analyze_content(request):
    """
    POST /analyze-content
    Accept text, image, video, audio, or transcription for moderation.
    """
    user_id = get_user_from_request(request)
    if not user_id:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    temp_files = []

    try:
        results = []

        # ── Handle text content ──
        text_content = request.POST.get('text', '') or ''
        if not text_content and request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                text_content = body.get('text', '')
            except (json.JSONDecodeError, Exception):
                pass

        if text_content:
            result = analyze_text_content(text_content, 'text')
            result['transcribed_text'] = None
            results.append(result)

            # Save moderation log
            log = moderation_log_document(
                user_id=user_id,
                content_type='text',
                status=result['status'],
                reason=result['reason'],
                confidence_score=result['confidence_score'],
                abusive_score=result['abusive_score'],
                categories_detected=result.get('categories_detected', []),
                corrected_text=result.get('corrected_text'),
            )
            save_moderation_log(log)
            track_content_submission(user_id, result)

        # ── Handle transcription (from frontend speech-to-text) ──
        transcription = request.POST.get('transcription', '')
        if transcription:
            result = analyze_text_content(transcription, 'voice-to-text')
            result['transcribed_text'] = transcription
            results.append(result)

            log = moderation_log_document(
                user_id=user_id,
                content_type='voice-to-text',
                status=result['status'],
                reason=result['reason'],
                confidence_score=result['confidence_score'],
                abusive_score=result['abusive_score'],
                categories_detected=result.get('categories_detected', []),
                corrected_text=result.get('corrected_text'),
                transcribed_text=transcription,
            )
            save_moderation_log(log)
            track_content_submission(user_id, result)

        # ── Handle file uploads ──
        files = request.FILES.getlist('files')
        if not files:
            # Try single file keys
            for key in ['image', 'video', 'audio', 'file']:
                f = request.FILES.get(key)
                if f:
                    files.append(f)

        for uploaded_file in files:
            content_type = get_content_type_from_file(uploaded_file.name)

            if content_type == 'image':
                file_path = save_uploaded_file(uploaded_file)
                temp_files.append(file_path)
                result = analyze_image_content(file_path, 'image')
                result['transcribed_text'] = None
                results.append(result)

            elif content_type == 'video':
                file_path = save_uploaded_file(uploaded_file)
                temp_files.append(file_path)
                result = analyze_video_content(file_path, 'video')
                result['transcribed_text'] = None
                results.append(result)

            elif content_type == 'audio':
                file_path = save_uploaded_audio(uploaded_file)
                temp_files.append(file_path)

                # Convert audio to text
                transcription_result = convert_audio_to_text(file_path)

                if transcription_result['success']:
                    transcribed = transcription_result['text']
                    result = analyze_text_content(transcribed, 'audio')
                    result['transcribed_text'] = transcribed
                else:
                    result = {
                        'content_type': 'audio',
                        'status': 'Approved',
                        'reason': f'Audio processed. Transcription note: {transcription_result["error"]}',
                        'confidence_score': 60,
                        'abusive_score': 0,
                        'categories_detected': [],
                        'corrected_text': None,
                        'transcribed_text': transcription_result.get('text', ''),
                    }

                results.append(result)

            else:
                results.append({
                    'content_type': 'unknown',
                    'status': 'Approved',
                    'reason': f'Unsupported file type: {uploaded_file.name}',
                    'confidence_score': 50,
                    'abusive_score': 0,
                    'categories_detected': [],
                    'corrected_text': None,
                    'transcribed_text': None,
                })

            # Save log for each file
            if results:
                latest = results[-1]
                log = moderation_log_document(
                    user_id=user_id,
                    content_type=latest['content_type'],
                    status=latest['status'],
                    reason=latest['reason'],
                    confidence_score=latest['confidence_score'],
                    abusive_score=latest['abusive_score'],
                    categories_detected=latest.get('categories_detected', []),
                    corrected_text=latest.get('corrected_text'),
                    transcribed_text=latest.get('transcribed_text'),
                    original_filename=uploaded_file.name,
                )
                save_moderation_log(log)
                track_content_submission(user_id, latest)

        if not results:
            return JsonResponse({
                'error': 'No content provided for analysis. Send text, transcription, or files.'
            }, status=400)

        # Check if admin alert should be sent
        alert_needed, behavior = should_send_alert(user_id)
        if alert_needed and behavior:
            send_admin_alert(behavior)

        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results),
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'error': f'Analysis failed: {str(e)}'
        }, status=500)

    finally:
        for fp in temp_files:
            cleanup_file(fp)


# ── User Behavior ────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def user_behavior(request):
    """
    GET /user-behavior
    Get behavior summary for the authenticated user.
    """
    user_id = get_user_from_request(request)
    if not user_id:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    summary = get_behavior_summary(user_id)

    # Also get recent moderation logs
    logs = get_user_moderation_logs(user_id, limit=20)
    history = []
    for log in logs:
        history.append({
            'content_type': log.get('content_type', 'unknown'),
            'status': log.get('status', ''),
            'reason': log.get('reason', ''),
            'confidence_score': log.get('confidence_score', 0),
            'abusive_score': log.get('abusive_score', 0),
            'created_at': str(log.get('created_at', '')),
            'original_filename': log.get('original_filename', ''),
            'transcribed_text': log.get('transcribed_text', ''),
        })

    summary['history'] = history

    return JsonResponse({
        'success': True,
        'behavior': summary,
    })


# ── Admin Alert ──────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def send_alert(request):
    """
    POST /send-alert
    Manually trigger an admin alert for a user.
    """
    user_id = get_user_from_request(request)
    if not user_id:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    behavior = get_behavior_summary(user_id)

    try:
        body = json.loads(request.body)
        reason = body.get('reason', 'Manual alert triggered')
    except (json.JSONDecodeError, Exception):
        reason = 'Manual alert triggered'

    sent = send_admin_alert(behavior, reason=reason)

    return JsonResponse({
        'success': True,
        'alert_sent': sent,
        'behavior': behavior,
    })


# ── Moderation History ───────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def moderation_history(request):
    """
    GET /moderation-history
    Get the moderation history for the authenticated user.
    """
    user_id = get_user_from_request(request)
    if not user_id:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    limit = int(request.GET.get('limit', 50))
    logs = get_user_moderation_logs(user_id, limit=limit)

    history = []
    for log in logs:
        history.append({
            'content_type': log.get('content_type', 'unknown'),
            'status': log.get('status', ''),
            'reason': log.get('reason', ''),
            'confidence_score': log.get('confidence_score', 0),
            'abusive_score': log.get('abusive_score', 0),
            'categories_detected': log.get('categories_detected', []),
            'corrected_text': log.get('corrected_text'),
            'transcribed_text': log.get('transcribed_text'),
            'original_filename': log.get('original_filename', ''),
            'created_at': str(log.get('created_at', '')),
        })

    return JsonResponse({
        'success': True,
        'history': history,
        'count': len(history),
    })


# ── Favicon (to avoid 404 spam) ─────────────────────────────

def favicon(request):
    """Return an empty 204 response for /favicon.ico requests.

    This prevents noisy 404 logs from browsers requesting the tab icon
    when no favicon is configured for the backend service.
    """
    return HttpResponse(status=204)
