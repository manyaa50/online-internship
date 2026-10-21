"""
app.services.notifications
==========================
Shared notifications service for SmartInternshipSystem.
Consolidates in-app notification creation across admin, auth, company,
internships, and reports blueprints.
"""
from app.models import db, Notification


def notify(user_id, title, message, category='general', link_url=None, auto_commit=False):
    """
    Creates and records an in-app notification for a specific user.

    Parameters:
        user_id (int): The ID of the recipient User.
        title (str): Short title of the notification.
        message (str): Detailed body content of the notification.
        category (str, optional): Category string (e.g., 'general', 'verification',
                                  'application', 'admin', 'scam_alert', 'report').
                                  Defaults to 'general'.
        link_url (str, optional): Target action URL for the notification.
        auto_commit (bool, optional): If True, commits the transaction immediately.
                                      Defaults to False so the notification participates
                                      in the caller's atomic transaction.

    Returns:
        Notification: The created and persisted (or staged) Notification instance.
    """
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category or 'general',
        link_url=link_url
    )
    db.session.add(notif)
    if auto_commit:
        db.session.commit()
    return notif
