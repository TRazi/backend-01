#!/usr/bin/env python
"""Debug bill endpoint registration."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

# Create test user
user = User.objects.filter(username='debugbill').first()
if not user:
    user = User.objects.create_user(
        username='debugbill',
        email='debugbill@test.com',
        password='test123'
    )

client = APIClient()
client.force_authenticate(user=user)

# Test endpoints
endpoints = [
    ('GET', '/api/v1/bills/'),
    ('GET', '/api/v1/receipts/'),
    ('OPTIONS', '/api/v1/bills/scan/'),
    ('OPTIONS', '/api/v1/receipts/scan/'),
    ('GET', '/api/v1/bills/scan/'),
    ('GET', '/api/v1/receipts/scan/'),
]

for method, path in endpoints:
    if method == 'GET':
        response = client.get(path)
    elif method == 'OPTIONS':
        response = client.options(path)
    print(f"{method} {path}: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"  Data keys: {list(response.data.keys()) if isinstance(response.data, dict) else 'N/A'}")

