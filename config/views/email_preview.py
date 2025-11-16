"""
Email Template Preview Views (Development Only)

These views allow developers to preview email templates in the browser.
Only accessible when DEBUG=True.
"""

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test


def is_debug_mode(user):
    """Only allow access in debug mode."""
    return settings.DEBUG


@user_passes_test(is_debug_mode)
def email_preview_list(request):
    """List all available email templates for preview."""
    templates = [
        {
            "name": "Email Verification",
            "url": "verify_email",
            "description": "Sent when a user signs up to verify their email address",
        },
        {
            "name": "Login OTP",
            "url": "login_otp",
            "description": "Sent when a user requests a one-time password for login",
        },
        {
            "name": "Welcome Email",
            "url": "welcome",
            "description": "Sent after a user successfully verifies their email",
        },
    ]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Template Previews</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4a90e2;
                padding-bottom: 10px;
            }
            .template-list {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .template-item {
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #4a90e2;
                background: #f8f9fa;
                border-radius: 4px;
            }
            .template-item h3 {
                margin: 0 0 5px 0;
                color: #2c3e50;
            }
            .template-item p {
                margin: 5px 0;
                color: #666;
                font-size: 14px;
            }
            .template-item a {
                display: inline-block;
                margin-top: 10px;
                padding: 8px 16px;
                background: #4a90e2;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
            }
            .template-item a:hover {
                background: #357abd;
            }
            .warning {
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="warning">
            ⚠️ <strong>Development Mode Only</strong> - These previews are only accessible when DEBUG=True
        </div>
        <h1>📧 Email Template Previews</h1>
        <div class="template-list">
    """

    for template in templates:
        html += f"""
            <div class="template-item">
                <h3>{template['name']}</h3>
                <p>{template['description']}</p>
                <a href="/emails/preview/{template['url']}/" target="_blank">Preview Template →</a>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """

    return HttpResponse(html)


@user_passes_test(is_debug_mode)
def preview_verify_email(request):
    """Preview the email verification template."""
    context = {
        "user": type(
            "User", (), {"first_name": "John", "email": "john.doe@example.com"}
        )(),
        "verification_url": "https://kinwise.co.nz/verify-email?token=abc123def456ghi789",
    }

    html = render_to_string("emails/verify_email.html", context)
    return HttpResponse(html)


@user_passes_test(is_debug_mode)
def preview_login_otp(request):
    """Preview the login OTP template."""
    context = {
        "user": type(
            "User", (), {"first_name": "John", "email": "kiaora@kinwise.co.nz"}
        )(),
        "otp_code": "123456",
    }

    html = render_to_string("emails/login_otp.html", context)
    return HttpResponse(html)


@user_passes_test(is_debug_mode)
def preview_welcome(request):
    """Preview the welcome email template."""
    context = {
        "user": type(
            "User", (), {"first_name": "John", "email": "john.doe@example.com"}
        )(),
    }

    html = render_to_string("emails/welcome.html", context)
    return HttpResponse(html)
