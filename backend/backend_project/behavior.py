"""User behavior tracking and categorization for Civility.ai."""

from django.conf import settings

from .mongo import (
    get_user_behavior,
    update_user_behavior,
    get_user_moderation_logs,
    get_collection,
)


def track_content_submission(user_id, moderation_result):
    """
    Track a content submission and update user behavior metrics.
    Called after every moderation check.
    """
    is_flagged = moderation_result.get('status') == 'Flagged'
    abusive_score = moderation_result.get('abusive_score', 0)

    behavior = update_user_behavior(user_id, is_flagged, abusive_score)
    return behavior


def _compute_behavior_trend(user_id):
    """Compute a simple behavior trend (increasing/decreasing/stable)."""
    logs = get_user_moderation_logs(user_id, limit=10)
    if not logs or len(logs) < 2:
        return 'unknown'

    # logs are returned newest-first; reverse to oldest-first
    ordered = list(reversed(logs))
    scores = [log.get('abusive_score', 0) or 0 for log in ordered]
    if len(scores) < 2:
        return 'unknown'

    first = scores[0]
    last = scores[-1]

    if last > first + 5:
        return 'increasing'
    if last < first - 5:
        return 'decreasing'
    return 'stable'


def evaluate_abuse_policy(user_id, abuse_score):
    """Evaluate policy actions based on a single post's abuse_score.

    Returns a dict matching the requested JSON policy format:
    {
      "abuse_score": number,
      "action": "allow|warn|delete_post|delete_account",
      "notify_user": bool,
      "notify_admin": bool,
      "repeat_offender": bool,
      "flagged_count": number,
      "reason": str,
      "behavior_trend": str,
    }
    """
    score = int(abuse_score or 0)

    # Recent history (rolling window of last 10 posts)
    recent_logs = get_user_moderation_logs(user_id, limit=10)

    # Total flagged within window (abuse_score > 25)
    total_flagged_window = 0
    for log in recent_logs:
        if int(log.get('abusive_score', 0) or 0) > 25:
            total_flagged_window += 1

    # Consecutive flagged posts from most recent backwards
    consecutive_prev = 0
    for log in recent_logs:
        prev_score = int(log.get('abusive_score', 0) or 0)
        if prev_score > 25:
            consecutive_prev += 1
        else:
            break

    flagged_current = score > 25
    if flagged_current:
        consecutive_flagged_count = consecutive_prev + 1
        flagged_count = total_flagged_window + 1
    else:
        # Reset consecutive counter when a clean post appears
        consecutive_flagged_count = 0
        flagged_count = 0

    # Repeat offender when either 3+ flagged in window or 3+ consecutive
    repeat_offender = flagged_count >= 3 or consecutive_flagged_count >= 3

    # Map abuse score ranges to actions (Cases 1–4)
    if score <= 25:
        action = 'allow'
        notify_user = False
        notify_admin = False
        policy_reason = 'Content is safe and respectful; allow without warning.'
    elif score <= 50:
        action = 'warn'
        notify_user = True
        # Admin alerted for repeat offenders (3+ flagged in window or consecutive)
        notify_admin = repeat_offender
        policy_reason = (
            'Mildly inappropriate or borderline toxic content; warn user and '
            'monitor for repeat behavior.'
        )
    elif score <= 75:
        action = 'delete_post'
        notify_user = True
        # For medium-severity abuse, only send admin email when the user is
        # a repeat offender (3+ flagged posts in the window or consecutive).
        notify_admin = repeat_offender
        if flagged_count >= 3:
            policy_reason = (
                'Clearly abusive or policy-violating content; block or delete '
                'this post and send a PRIORITY alert to admin because this '
                'user is now high-risk (3+ flagged posts in the recent window).'
            )
        else:
            policy_reason = (
                'Clearly abusive or policy-violating content; block or delete '
                'this post and monitor for further violations.'
            )
    else:
        action = 'delete_account'
        notify_user = True
        notify_admin = True
        policy_reason = (
            'Severe abuse or hate content; remove content and suspend or '
            'delete the user account, notify admin.'
        )

    behavior_trend = _compute_behavior_trend(user_id)

    # If action is delete_account, optionally mark user as suspended.
    # Controlled by ENABLE_ACCOUNT_SUSPENSION so that development/demo
    # environments don't permanently block users.
    if action == 'delete_account' and getattr(settings, 'ENABLE_ACCOUNT_SUSPENSION', False):
        try:
            users = get_collection('users')
            users.update_one({'user_id': user_id}, {'$set': {'status': 'suspended'}})
        except Exception:
            pass

    return {
        'abuse_score': score,
        'action': action,
        'notify_user': notify_user,
        'notify_admin': notify_admin,
        'repeat_offender': repeat_offender,
        'flagged_count': flagged_count,
        'consecutive_flagged_count': consecutive_flagged_count,
        'reason': policy_reason,
        'behavior_trend': behavior_trend,
    }


def get_behavior_summary(user_id):
    """Get a comprehensive behavior summary for a user."""
    behavior = get_user_behavior(user_id)

    if not behavior:
        return {
            'user_id': user_id,
            'total_uploads': 0,
            'flagged_count': 0,
            'abuse_score': 0,
            'behavior_category': 'Safe',
            'approval_rate': 100,
            'recent_flags': [],
            'risk_level': 'low',
            'avg_confidence_score': 100,
        }

    total = behavior['total_uploads']
    flagged = behavior['flagged_count']
    approval_rate = round(((total - flagged) / total * 100), 1) if total > 0 else 100

    # Compute average abusive score and confidence across all moderation logs
    # for this user. This reflects the user's overall behavior history.
    avg_abuse = behavior['abuse_score']
    avg_confidence = 100
    try:
        agg = list(get_collection('moderation_logs').aggregate([
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': None,
                'avg_abusive': {'$avg': '$abusive_score'},
                'avg_confidence': {'$avg': '$confidence_score'},
            }},
        ]))

        if agg:
            doc = agg[0]
            if doc.get('avg_abusive') is not None:
                avg_abuse = round(doc['avg_abusive'], 1)
            if doc.get('avg_confidence') is not None:
                avg_confidence = round(doc['avg_confidence'], 1)
    except Exception:
        # Fall back silently to behavior document values if aggregation fails
        pass

    # Get recent flagged entries
    logs = get_user_moderation_logs(user_id, limit=10)
    recent_flags = [
        {
            'content_type': log.get('content_type', 'unknown'),
            'reason': log.get('reason', ''),
            'abusive_score': log.get('abusive_score', 0),
            'created_at': str(log.get('created_at', '')),
        }
        for log in logs if log.get('status') == 'Flagged'
    ]

    # Determine risk level based on the averaged abuse score
    abuse_score = avg_abuse
    if abuse_score < 20:
        risk_level = 'low'
    elif abuse_score < 45:
        risk_level = 'medium'
    elif abuse_score < 70:
        risk_level = 'high'
    else:
        risk_level = 'critical'

    return {
        'user_id': behavior['user_id'],
        'email': behavior.get('email', ''),
        'name': behavior.get('name', ''),
        'total_uploads': total,
        'flagged_count': flagged,
        'abuse_score': abuse_score,
        'behavior_category': behavior['behavior_category'],
        'approval_rate': approval_rate,
        'recent_flags': recent_flags,
        'risk_level': risk_level,
        'avg_confidence_score': avg_confidence,
    }


def should_send_alert(user_id):
    """
    Determine if an admin alert should be sent for this user.
    Triggers when:
    - Abuse score exceeds 60
    - More than 3 flagged items in recent submissions
    - Behavior category is 'Risky' or 'Critical'
    """
    behavior = get_user_behavior(user_id)

    if not behavior:
        return False, None

    if behavior['abuse_score'] >= 60 or behavior['behavior_category'] in ('Risky', 'Critical'):
        return True, behavior

    if behavior['flagged_count'] >= 3 and behavior['total_uploads'] > 0:
        flag_rate = behavior['flagged_count'] / behavior['total_uploads']
        if flag_rate > 0.5:
            return True, behavior

    return False, None
