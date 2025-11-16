from apps.users.models import User

# Get all users
users = User.objects.all().order_by("id")

print(f"Total users: {users.count()}")
print(f"Users with username: {users.filter(username__isnull=False).count()}")
print(f"Users without username: {users.filter(username__isnull=True).count()}")
print("\n" + "=" * 80)
print("USER DETAILS:")
print("=" * 80)

for user in users:
    print(f"ID: {user.id:2} | Email: {user.email:35} | Username: {user.username}")

# Verify uniqueness
usernames = list(users.values_list("username", flat=True))
unique_usernames = {u for u in usernames if u is not None}
print("\n" + "=" * 80)
print("Username Uniqueness Check:")
print(f"  Total usernames: {len([u for u in usernames if u is not None])}")
print(f"  Unique usernames: {len(unique_usernames)}")
print(
    f"  Duplicates: {len([u for u in usernames if u is not None]) - len(unique_usernames)}"
)
print("=" * 80)

if len(unique_usernames) == len([u for u in usernames if u is not None]):
    print("✅ All usernames are unique!")
else:
    print("❌ Duplicate usernames detected!")
