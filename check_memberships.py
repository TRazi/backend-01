#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from households.models import Membership

types = Membership.objects.values("membership_type").distinct()
print("Membership types in database:")
for t in types:
    count = Membership.objects.filter(membership_type=t["membership_type"]).count()
    mt = t["membership_type"]
    print(f"  '{mt}': {count} memberships")

print(f"\nTotal: {Membership.objects.count()}")
