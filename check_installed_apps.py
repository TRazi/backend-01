import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

from django.conf import settings

print("\n=== INSTALLED_APPS ===")
for i, app in enumerate(settings.INSTALLED_APPS, 1):
    print(f"{i:2d}. {app}")
print(f"\nTotal: {len(settings.INSTALLED_APPS)} apps")

# Check for config.apps specifically
if 'config.apps.ConfigAppConfig' in settings.INSTALLED_APPS:
    print("\n⚠️  FOUND: config.apps.ConfigAppConfig in INSTALLED_APPS")
    idx = settings.INSTALLED_APPS.index('config.apps.ConfigAppConfig')
    print(f"   Position: {idx + 1}")
