import glob
from django.http import FileResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
# Debug endpoint to download the last received audio file
@csrf_exempt
@require_http_methods(["GET"])
def download_last_audio(request):
    """Download the most recent audio file received for debugging."""
    import os
    debug_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'audio_debug'))
    files = sorted(glob.glob(os.path.join(debug_dir, '*')), reverse=True)
    if not files:
        return JsonResponse({'error': 'No audio files found.'}, status=404)
    latest = files[0]
    return FileResponse(open(latest, 'rb'), as_attachment=True, filename=os.path.basename(latest))
"""API Views for Civility.ai backend."""

import json
import os
import traceback
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response

from moderation.models import Content

from .auth import (
    get_user_from_request,
    login_with_google,
    login_with_password,
    register_local_user,
)
from .gemini import analyze_text_content, analyze_image_content, analyze_video_content
from .voice import convert_audio_to_text, save_uploaded_audio, cleanup_audio_file
from .mongo import save_moderation_log, get_user_moderation_logs, find_user_by_id
from .behavior import track_content_submission, get_behavior_summary, should_send_alert, evaluate_abuse_policy
from .utils import (
    save_uploaded_file,
    cleanup_file,
    get_content_type_from_file,
    send_admin_alert,
    send_user_warning_email,
    send_user_violation_email,
    send_admin_alert_email,
    blur_image_to_media,
)
from .models import moderation_log_document


def _apply_policy_notifications(user_id, result, policy):
    """Send user and admin notifications based on policy evaluation."""
    try:
        user = find_user_by_id(user_id)
    except Exception:
        user = None

    user_email = user.get('email') if user else None

    # User notifications (via spec-named helpers)
    if policy.get('notify_user') and user_email:
        action = policy.get('action')
        abuse_score = policy.get('abuse_score')

        if action == 'warn':
            send_user_warning_email(user_email, abuse_score)
        elif action in ('delete_post', 'delete_account'):
            send_user_violation_email(user_email, abuse_score, action)

    # Admin notifications
    if policy.get('notify_admin'):
        behavior = get_behavior_summary(user_id)
        recent_logs = get_user_moderation_logs(user_id, limit=5)

        # Build a compact summary of recent flagged items
        lines = []
        for log in recent_logs:
            ts = str(log.get('created_at', ''))
            score = log.get('abusive_score', 0)
            ctype = log.get('content_type', 'unknown')
            snippet = log.get('transcribed_text') or log.get('original_filename', '(no content stored)')
            if isinstance(snippet, str) and len(snippet) > 120:
                snippet = snippet[:117] + '...'
            lines.append(f'- [{ts}] ({ctype}) score={score}, content={snippet}')

        behavior_trend = policy.get('behavior_trend', 'unknown')

        reason = (
            f"Policy action: {policy.get('action')} | abuse_score={policy.get('abuse_score')} | "
            f"flagged_count_window={policy.get('flagged_count')} | "
            f"consecutive_flagged={policy.get('consecutive_flagged_count', 0)} | "
            f"repeat_offender={policy.get('repeat_offender')} | "
            f"trend={behavior_trend}.\nRecent items:\n" + '\n'.join(lines)
        )

        send_admin_alert_email(behavior, reason=reason)


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
def email_register(request):
    """POST /auth/register

    Register a new user with email and password.
    """
    try:
        body = json.loads(request.body)
        email = body.get('email', '')
        password = body.get('password', '')
        name = body.get('name', '')

        result, error = register_local_user(email, password, name)
        if error:
            return JsonResponse({'error': error}, status=400)

        # Include a success flag so the frontend LoginPage can
        # reliably detect successful registration and log the user in.
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
@require_http_methods(["POST"])
def email_login(request):
    """POST /auth/login

    Authenticate an existing user via email and password.
    """
    try:
        body = json.loads(request.body)
        email = body.get('email', '')
        password = body.get('password', '')

        result, error = login_with_password(email, password)
        if error:
            return JsonResponse({'error': error}, status=401)

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
@require_http_methods(["POST"])
def google_login(request):
    """POST /auth/google-login

    Accept Google OAuth token, verify, create/update user, return JWT.
    """
    try:
        body = json.loads(request.body)
        google_token = body.get('token', '')

        if not google_token:
            return JsonResponse({'error': 'Google token is required'}, status=400)

        result, error = login_with_google(google_token)

        if error:
            return JsonResponse({'error': error}, status=401)

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

    # Prevent banned / suspended users from posting, but only when
    # account suspension is explicitly enabled.
    user_doc = find_user_by_id(user_id)
    if (
        getattr(settings, 'ENABLE_ACCOUNT_SUSPENSION', False)
        and user_doc
        and user_doc.get('status') == 'suspended'
    ):
        return JsonResponse({
            'error': 'Account is suspended due to severe policy violations.',
            'action': 'delete_account',
        }, status=403)

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

            # Apply abuse policy for this submission
            policy = evaluate_abuse_policy(user_id, result.get('abusive_score', 0))
            result['abuse_policy'] = policy
            result['abuse_score'] = policy['abuse_score']
            result['action'] = policy['action']
            result['notify_user'] = policy['notify_user']
            result['notify_admin'] = policy['notify_admin']
            result['repeat_offender'] = policy['repeat_offender']
            result['flagged_count'] = policy['flagged_count']

            results.append(result)

            # Save moderation log with policy info
            log = moderation_log_document(
                user_id=user_id,
                content_type='text',
                status=result['status'],
                reason=result['reason'],
                confidence_score=result['confidence_score'],
                abusive_score=result['abusive_score'],
                categories_detected=result.get('categories_detected', []),
                corrected_text=result.get('corrected_text'),
                transcribed_text=text_content,
            )
            log['abuse_action'] = policy['action']
            log['repeat_offender'] = policy['repeat_offender']
            log['flagged_count'] = policy['flagged_count']

            save_moderation_log(log)
            track_content_submission(user_id, result)

            # Notifications
            _apply_policy_notifications(user_id, result, policy)

            # Also persist to Django ORM Content model so signals can
            # trigger admin alerts based on flagged_count/score
            try:
                # Compute flagged_count locally using Django ORM so it
                # doesn't depend on MongoDB connectivity.
                abuse_score = policy.get('abuse_score', 0) or 0
                email = (user_doc or {}).get('email', '')
                flagged_count_orm = 0
                if abuse_score > 25 and email:
                    last = Content.objects.filter(user_email=email).order_by('-id').first()
                    prev = last.flagged_count if last else 0
                    flagged_count_orm = prev + 1

                Content.objects.create(
                    text=text_content,
                    flagged_count=flagged_count_orm,
                    score=abuse_score,
                    user_email=email,
                )
            except Exception:
                pass

        # ── Handle transcription (from frontend speech-to-text) ──
        transcription = request.POST.get('transcription', '')
        if transcription:
            result = analyze_text_content(transcription, 'voice-to-text')
            result['transcribed_text'] = transcription

            policy = evaluate_abuse_policy(user_id, result.get('abusive_score', 0))
            result['abuse_policy'] = policy
            result['abuse_score'] = policy['abuse_score']
            result['action'] = policy['action']
            result['notify_user'] = policy['notify_user']
            result['notify_admin'] = policy['notify_admin']
            result['repeat_offender'] = policy['repeat_offender']
            result['flagged_count'] = policy['flagged_count']

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
            log['abuse_action'] = policy['action']
            log['repeat_offender'] = policy['repeat_offender']
            log['flagged_count'] = policy['flagged_count']

            save_moderation_log(log)
            track_content_submission(user_id, result)
            _apply_policy_notifications(user_id, result, policy)

            try:
                abuse_score = policy.get('abuse_score', 0) or 0
                email = (user_doc or {}).get('email', '')
                flagged_count_orm = 0
                if abuse_score > 25 and email:
                    last = Content.objects.filter(user_email=email).order_by('-id').first()
                    prev = last.flagged_count if last else 0
                    flagged_count_orm = prev + 1

                Content.objects.create(
                    text=transcription,
                    flagged_count=flagged_count_orm,
                    score=abuse_score,
                    user_email=email,
                )
            except Exception:
                pass

        # ── Handle file uploads ──
        files = request.FILES.getlist('files')
        if not files:
            # Try single file keys
            for key in ['image', 'video', 'audio', 'file']:
                f = request.FILES.get(key)
                if f:
                    files.append(f)

        for uploaded_file in files:
            # Prefer MIME type from the upload when available so that
            # audio recordings (e.g. audio/webm from MediaRecorder)
            # are correctly routed to the audio transcription path.
            content_type = None
            mime_type = getattr(uploaded_file, 'content_type', '') or ''

            if mime_type.startswith('image/'):
                content_type = 'image'
            elif mime_type.startswith('video/'):
                content_type = 'video'
            elif mime_type.startswith('audio/'):
                content_type = 'audio'

            if not content_type:
                content_type = get_content_type_from_file(uploaded_file.name)

            if content_type == 'image':
                file_path = save_uploaded_file(uploaded_file)
                temp_files.append(file_path)
                result = analyze_image_content(file_path, 'image')
                result['transcribed_text'] = None

                policy = evaluate_abuse_policy(user_id, result.get('abusive_score', 0))
                result['abuse_policy'] = policy
                result['abuse_score'] = policy['abuse_score']
                result['action'] = policy['action']
                result['notify_user'] = policy['notify_user']
                result['notify_admin'] = policy['notify_admin']
                result['repeat_offender'] = policy['repeat_offender']
                result['flagged_count'] = policy['flagged_count']

                # If image is inappropriate (e.g. nudity / high abuse score),
                # generate a blurred version and return its URL.
                cats = [c.lower() for c in result.get('categories_detected', [])]
                needs_blur = (
                    any('nudity' in c or 'sexual' in c for c in cats)
                    or result.get('abusive_score', 0) >= 60
                )
                if needs_blur:
                    blurred_url = blur_image_to_media(file_path, uploaded_file.name)
                    if blurred_url:
                        result['is_blurred'] = True
                        result['blurred_image_url'] = blurred_url

                results.append(result)

            elif content_type == 'video':
                file_path = save_uploaded_file(uploaded_file)
                temp_files.append(file_path)
                result = analyze_video_content(file_path, 'video')
                result['transcribed_text'] = None

                policy = evaluate_abuse_policy(user_id, result.get('abusive_score', 0))
                result['abuse_policy'] = policy
                result['abuse_score'] = policy['abuse_score']
                result['action'] = policy['action']
                result['notify_user'] = policy['notify_user']
                result['notify_admin'] = policy['notify_admin']
                result['repeat_offender'] = policy['repeat_offender']
                result['flagged_count'] = policy['flagged_count']

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

                    policy = evaluate_abuse_policy(user_id, result.get('abusive_score', 0))
                    result['abuse_policy'] = policy
                    result['abuse_score'] = policy['abuse_score']
                    result['action'] = policy['action']
                    result['notify_user'] = policy['notify_user']
                    result['notify_admin'] = policy['notify_admin']
                    result['repeat_offender'] = policy['repeat_offender']
                    result['flagged_count'] = policy['flagged_count']
                    try:
                        abuse_score = policy.get('abuse_score', 0) or 0
                        email = (user_doc or {}).get('email', '')
                        flagged_count_orm = 0
                        if abuse_score > 25 and email:
                            last = Content.objects.filter(user_email=email).order_by('-id').first()
                            prev = last.flagged_count if last else 0
                            flagged_count_orm = prev + 1

                        Content.objects.create(
                            text=transcribed,
                            flagged_count=flagged_count_orm,
                            score=abuse_score,
                            user_email=email,
                        )
                    except Exception:
                        pass
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
                tmp_result = {
                    'content_type': 'unknown',
                    'status': 'Approved',
                    'reason': f'Unsupported file type: {uploaded_file.name}',
                    'confidence_score': 50,
                    'abusive_score': 0,
                    'categories_detected': [],
                    'corrected_text': None,
                    'transcribed_text': None,
                }

                policy = evaluate_abuse_policy(user_id, tmp_result.get('abusive_score', 0))
                tmp_result['abuse_policy'] = policy
                tmp_result['abuse_score'] = policy['abuse_score']
                tmp_result['action'] = policy['action']
                tmp_result['notify_user'] = policy['notify_user']
                tmp_result['notify_admin'] = policy['notify_admin']
                tmp_result['repeat_offender'] = policy['repeat_offender']
                tmp_result['flagged_count'] = policy['flagged_count']

                results.append(tmp_result)

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

                policy = latest.get('abuse_policy') or evaluate_abuse_policy(
                    user_id, latest.get('abusive_score', 0)
                )
                log['abuse_action'] = policy['action']
                log['repeat_offender'] = policy['repeat_offender']
                log['flagged_count'] = policy['flagged_count']

                save_moderation_log(log)
                track_content_submission(user_id, latest)
                _apply_policy_notifications(user_id, latest, policy)

        if not results:
            return JsonResponse({
                'error': 'No content provided for analysis. Send text, transcription, or files.'
            }, status=400)

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


# ── Audio Transcription (Voice-to-Text) ─────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio(request):
    """POST /transcribe-audio

    Accept a single audio file, convert it to text using the existing
    speech recognition pipeline, and return only the transcription.

    This is used by the frontend voice-to-text feature when browser
    speech recognition is unavailable or unreliable.
    """
    # Authentication is optional for transcription-only; if you want to
    # restrict it, uncomment the token check below.
    # user_id = get_user_from_request(request)
    # if not user_id:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)

    uploaded_file = None
    for key in ["file", "audio", "voice"]:
        if key in request.FILES:
            uploaded_file = request.FILES[key]
            break

    if not uploaded_file:
        return JsonResponse({
            'success': False,
            'text': '',
            'error': 'No audio file provided. Use form field name "file".',
        }, status=400)

    temp_path = None
    try:
        temp_path = save_uploaded_audio(uploaded_file)
        result = convert_audio_to_text(temp_path)
        return JsonResponse({
            'success': result.get('success', False),
            'text': result.get('text', ''),
            'error': result.get('error', None),
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'text': '',
            'error': f'Transcription failed: {str(e)}',
        }, status=500)
    finally:
        if temp_path:
            cleanup_audio_file(temp_path)


# ── Simple Speech-to-Text endpoint (DRF) ───────────────────

@api_view(['POST'])
def speech_to_text(request):
    """Accept an uploaded audio file and return its transcription.

    This uses the existing audio pipeline (pydub + SpeechRecognition)
    via convert_audio_to_text(), which supports common formats like
    webm/ogg/wav that the browser MediaRecorder produces.

    The endpoint always returns HTTP 200 for well-formed requests and
    uses a ``success`` flag in the JSON body to indicate whether
    speech recognition succeeded. This avoids noisy 400 responses when
    audio cannot be understood while still surfacing a clear error
    message to the frontend.
    """

    # Accept common field names used by different clients.
    uploaded_file = (
        request.FILES.get('audio')
        or request.FILES.get('file')
        or request.FILES.get('voice')
    )

    if not uploaded_file:
        return Response({
            'success': False,
            'text': '',
            'error': 'No audio file provided (expected field name "audio")',
        }, status=200)

    temp_path = None
    try:
        temp_path = save_uploaded_audio(uploaded_file)
        result = convert_audio_to_text(temp_path)

        success = bool(result.get('success'))
        text = result.get('text', '')
        error_msg = result.get('error')

        # Always return 200 for a valid request; the frontend can use
        # the "success" flag and error message to decide what to show.
        return Response({
            'success': success,
            'text': text,
            'error': error_msg if not success else None,
        }, status=200)
    except Exception as e:
        return Response({
            'success': False,
            'text': '',
            'error': f'Transcription failed: {str(e)}',
        }, status=500)
    finally:
        if temp_path:
            cleanup_audio_file(temp_path)

