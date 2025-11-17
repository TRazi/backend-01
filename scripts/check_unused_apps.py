#!/usr/bin/env python
"""
Script to check which installed Django apps are not being used in the project.

Usage:
    python check_unused_apps.py

This script analyzes:
1. INSTALLED_APPS from settings
2. URL configurations
3. Import statements across the codebase
4. Model references
5. Admin registrations
6. Middleware usage
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Django setup
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))

# Set Django settings before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from django.conf import settings
from django.apps import apps


def get_installed_apps():
    """Get all installed apps from settings."""
    return settings.INSTALLED_APPS


def check_url_usage(app_name):
    """Check if app is referenced in URL configurations."""
    url_files = [
        BASE_DIR / "config" / "urls.py",
        BASE_DIR / "config" / "api_v1_urls.py",
    ]
    
    patterns = [
        rf'include\(["\']({app_name}\.urls|{app_name}\.api_urls)["\']',
        rf'from {app_name}',
        rf'import.*{app_name}',
    ]
    
    for url_file in url_files:
        if url_file.exists():
            content = url_file.read_text(encoding='utf-8')
            for pattern in patterns:
                if re.search(pattern, content):
                    return True, f"Found in {url_file.name}"
    
    return False, "Not found in URL configs"


def check_imports_in_codebase(app_name):
    """Check if app is imported anywhere in the codebase."""
    import_count = 0
    locations = []
    
    # Search in Python files
    for py_file in BASE_DIR.rglob("*.py"):
        # Skip virtual environments, migrations, and cache
        if any(skip in str(py_file) for skip in ["venv", "env", "__pycache__", "migrations", ".pytest_cache"]):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8')
            patterns = [
                rf'^from {app_name}',
                rf'^import {app_name}',
                rf'from {app_name}\.',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    import_count += 1
                    locations.append(str(py_file.relative_to(BASE_DIR)))
                    break
        except Exception:
            continue
    
    return import_count, locations


def check_models_usage(app_name):
    """Check if app has models and if they're used."""
    try:
        app_config = apps.get_app_config(app_name.split('.')[-1])
        models = app_config.get_models()
        
        if not models:
            return False, "No models defined"
        
        model_names = [model.__name__ for model in models]
        return True, f"Has models: {', '.join(model_names[:3])}{'...' if len(model_names) > 3 else ''}"
    except LookupError:
        return False, "App config not found"


def check_admin_registration(app_name):
    """Check if app has admin registrations."""
    admin_file = None
    
    # Try to find admin.py
    if '.' in app_name:
        parts = app_name.split('.')
        admin_file = BASE_DIR / "apps" / parts[-1] / "admin.py"
    else:
        admin_file = BASE_DIR / "apps" / app_name / "admin.py"
    
    if admin_file and admin_file.exists():
        content = admin_file.read_text(encoding='utf-8')
        if re.search(r'admin\.site\.register', content):
            return True, "Has admin registrations"
    
    return False, "No admin registrations"


def check_middleware_usage(app_name):
    """Check if app provides middleware being used."""
    middleware_list = settings.MIDDLEWARE
    
    for middleware in middleware_list:
        if app_name in middleware:
            return True, f"Used as middleware: {middleware}"
    
    return False, "Not used as middleware"


def analyze_app_usage():
    """Main analysis function."""
    installed_apps = get_installed_apps()
    
    results = {
        'used': [],
        'possibly_unused': [],
        'core_django': [],
        'third_party': [],
    }
    
    # Categorize Django core apps
    django_core_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ]
    
    # Known third-party apps that are essential
    essential_third_party = {
        'rest_framework': 'DRF - API framework',
        'drf_spectacular': 'API documentation',
        'corsheaders': 'CORS handling',
        'axes': 'Security - brute force protection',
        'unfold': 'Admin UI enhancement',
        'django_celery_beat': 'Celery scheduling',
        'django_celery_results': 'Celery results storage',
    }
    
    print("=" * 80)
    print("DJANGO INSTALLED APPS USAGE ANALYSIS")
    print("=" * 80)
    print()
    
    for app in installed_apps:
        app_name = app.split('.')[-1]
        
        # Skip Django core apps
        if app in django_core_apps:
            results['core_django'].append(app)
            continue
        
        print(f"\n{'─' * 80}")
        print(f"Analyzing: {app}")
        print(f"{'─' * 80}")
        
        usage_indicators = []
        
        # Check various usage patterns
        url_used, url_msg = check_url_usage(app_name)
        if url_used:
            usage_indicators.append(f"✓ URLs: {url_msg}")
        else:
            print(f"  ✗ URLs: {url_msg}")
        
        import_count, locations = check_imports_in_codebase(app_name)
        if import_count > 0:
            usage_indicators.append(f"✓ Imports: {import_count} files")
            if len(locations) <= 5:
                for loc in locations:
                    print(f"    - {loc}")
        else:
            print(f"  ✗ Imports: Not found in codebase")
        
        has_models, model_msg = check_models_usage(app_name)
        if has_models:
            usage_indicators.append(f"✓ Models: {model_msg}")
        
        has_admin, admin_msg = check_admin_registration(app_name)
        if has_admin:
            usage_indicators.append(f"✓ Admin: {admin_msg}")
        
        is_middleware, mw_msg = check_middleware_usage(app_name)
        if is_middleware:
            usage_indicators.append(f"✓ Middleware: {mw_msg}")
        
        # Check if it's a known essential third-party app
        if app_name in essential_third_party:
            usage_indicators.append(f"✓ Essential: {essential_third_party[app_name]}")
        
        # Print usage indicators
        if usage_indicators:
            print(f"\n  Usage indicators:")
            for indicator in usage_indicators:
                print(f"    {indicator}")
            results['used'].append((app, usage_indicators))
        else:
            print(f"\n  ⚠️  WARNING: No usage indicators found!")
            results['possibly_unused'].append(app)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\n✓ Django Core Apps ({len(results['core_django'])}):")
    for app in results['core_django']:
        print(f"  - {app}")
    
    print(f"\n✓ Used Apps ({len(results['used'])}):")
    for app, indicators in results['used']:
        print(f"  - {app} ({len(indicators)} indicators)")
    
    if results['possibly_unused']:
        print(f"\n⚠️  Possibly Unused Apps ({len(results['possibly_unused'])}):")
        print("  These apps have no detected usage - verify before removing!")
        for app in results['possibly_unused']:
            print(f"  - {app}")
    else:
        print(f"\n✓ All non-core apps appear to be in use!")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. Django core apps (django.contrib.*) should NOT be removed unless you know
   exactly what you're doing.

2. Third-party apps (rest_framework, corsheaders, etc.) are typically essential
   for functionality even if not directly imported.

3. For "possibly unused" apps:
   - Check if they're used in migrations
   - Check if they provide settings/configuration
   - Check if they're required by other installed apps
   - Search for their usage in templates
   - Review their documentation for passive functionality

4. Apps with low usage might still be needed:
   - Some apps work via signals or middleware
   - Some apps are only used in specific environments
   - Some apps provide management commands

5. To verify an app is truly unused:
   - Remove it from INSTALLED_APPS temporarily
   - Run: python manage.py check
   - Run: python manage.py makemigrations --dry-run
   - Run your test suite
   - Try accessing all major features
""")


if __name__ == "__main__":
    analyze_app_usage()
