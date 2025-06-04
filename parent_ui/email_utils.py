from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

def send_verification_email(user, request):
    """Send email verification email to user"""
    try:
        # Generate new verification token
        user.email_verification_token = uuid.uuid4()
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        # Build verification URL
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': user.email_verification_token})
        )
        
        # Email context
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'Parental Control System',
            'expires_hours': settings.EMAIL_VERIFICATION_TOKEN_EXPIRES_HOURS,
        }
        
        # Render email templates
        html_message = render_to_string('parent_ui/emails/verification_email.html', context)
        plain_message = render_to_string('parent_ui/emails/verification_email.txt', context)
        
        # Send email
        send_mail(
            subject='Verify Your Email Address - Parental Control System',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        return False

def verify_email_token(token):
    """Verify email token and activate user if valid"""
    from api.models import CustomUser
    
    try:
        # Find user with this token
        user = CustomUser.objects.get(email_verification_token=token)
        
        # Check if token has expired
        if user.email_verification_sent_at:
            expiry_time = user.email_verification_sent_at + timedelta(
                hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRES_HOURS
            )
            if timezone.now() > expiry_time:
                return None, "Verification link has expired. Please request a new one."
        
        # Check if already verified
        if user.is_email_verified:
            return user, "Email already verified."
        
        # Verify email and activate user
        user.is_email_verified = True
        user.is_active = True
        user.save()
        
        logger.info(f"Email verified for user {user.username}")
        return user, "Email verified successfully!"
        
    except CustomUser.DoesNotExist:
        return None, "Invalid verification link."
    except Exception as e:
        logger.error(f"Error verifying email token {token}: {str(e)}")
        return None, "An error occurred during verification."

def resend_verification_email(user, request):
    """Resend verification email if user is not verified"""
    if user.is_email_verified:
        return False, "Email is already verified."
    
    # Check if last email was sent recently (prevent spam)
    if user.email_verification_sent_at:
        time_since_last = timezone.now() - user.email_verification_sent_at
        if time_since_last < timedelta(minutes=5):
            remaining_minutes = 5 - int(time_since_last.total_seconds() / 60)
            return False, f"Please wait {remaining_minutes} minutes before requesting another email."
    
    success = send_verification_email(user, request)
    if success:
        return True, "Verification email sent successfully."
    else:
        return False, "Failed to send verification email. Please try again later."
