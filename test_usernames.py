import sys

sys.path.insert(0, ".")

if __name__ == "__main__":
    import django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    django.setup()

    from django.db import connection

    cursor = connection.cursor()
    cursor.execute("SELECT id, email, username FROM users ORDER BY id;")
    rows = cursor.fetchall()

    print(f"Total users: {len(rows)}")
    print("\nUSER DETAILS:")
    print("=" * 80)
    print(f"{'ID':3} | {'Email':<35} | {'Username':<20}")
    print("=" * 80)

    for row_id, email, username in rows:
        print(f"{row_id:3} | {email:<35} | {username}")

    # Check uniqueness
    usernames = [row[2] for row in rows if row[2] is not None]
    print("\n" + "=" * 80)
    print("Username Uniqueness Check:")
    print(f"  Total usernames: {len(usernames)}")
    print(f"  Unique usernames: {len(set(usernames))}")
    print(f"  Duplicates: {len(usernames) - len(set(usernames))}")
    print("=" * 80)

    if len(set(usernames)) == len(usernames):
        print("✅ All usernames are unique!")
    else:
        print("❌ Duplicate usernames detected!")
