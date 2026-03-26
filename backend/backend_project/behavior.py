"""
User behavior tracking and categorization for Civility.ai
"""

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
        }

    total = behavior['total_uploads']
    flagged = behavior['flagged_count']
    approval_rate = round(((total - flagged) / total * 100), 1) if total > 0 else 100

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

    # Determine risk level
    abuse_score = behavior['abuse_score']
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
