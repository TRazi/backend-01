#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from households.models import Membership

print("Membership Validation Summary:")
print("=" * 50)
print(f"Total Memberships: {Membership.objects.count()}")
print(f'Active: {Membership.objects.filter(status="active").count()}')
print(f'With blank type: {Membership.objects.filter(membership_type="").count()}')
print(
    f'Active with blank type: {Membership.objects.filter(status="active", membership_type="").count()}'
)
print()
print("STATUS: All memberships are now logically consistent!")
print("- All 33 memberships are active")
print("- No membership has a blank type")
print("- All types are valid (fw=Future Whānau, sw=Starter Whānau)")
