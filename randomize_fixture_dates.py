#!/usr/bin/env python
"""
Randomize created_at and updated_at dates in fixture files.
Distributes dates randomly over the past 3 years.
"""
import json
import random
from datetime import datetime, timedelta
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

# Define date range: past 3 years
end_date = datetime.now()
start_date = end_date - timedelta(days=3 * 365)


def random_datetime_in_range(start, end):
    """Generate a random datetime between start and end."""
    time_between = end - start
    random_days = random.randint(0, time_between.days)
    random_seconds = random.randint(0, 86400)  # seconds in a day
    return start + timedelta(days=random_days, seconds=random_seconds)


def randomize_dates_in_fixture(file_path):
    """Randomize created_at and updated_at dates in a fixture file."""
    print(f"\nProcessing: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Track date assignments per model to ensure logical ordering
    model_dates = {}

    for item in data:
        model = item["model"]
        pk = item.get("pk")
        fields = item.get("fields", {})

        # Generate random created_at
        if "created_at" in fields:
            # Use existing date or generate new one
            if (model, pk) not in model_dates:
                created_at = random_datetime_in_range(start_date, end_date)
                model_dates[(model, pk)] = created_at
            else:
                created_at = model_dates[(model, pk)]

            fields["created_at"] = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Set updated_at to be same or later than created_at
            if "updated_at" in fields:
                # 70% chance it's the same, 30% chance it's been updated
                if random.random() < 0.7:
                    updated_at = created_at
                else:
                    # Updated sometime between creation and now
                    updated_at = random_datetime_in_range(created_at, end_date)

                fields["updated_at"] = updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Handle related timestamps
        if "last_login" in fields and fields["last_login"]:
            # Last login should be after creation
            if "created_at" in fields:
                user_created = datetime.strptime(
                    fields["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                last_login = random_datetime_in_range(user_created, end_date)
                fields["last_login"] = last_login.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Transaction dates should be logical
        if model == "transactions.Transaction" and "transaction_date" in fields:
            if "created_at" in fields:
                created = datetime.strptime(
                    fields["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                # Transaction date could be before created_at (manual entry of old transactions)
                # But usually within a few days
                if random.random() < 0.8:
                    # 80% of the time, transaction date is within a week of creation
                    trans_date = created - timedelta(days=random.randint(0, 7))
                else:
                    # 20% of the time, it's an older transaction being entered
                    trans_date = created - timedelta(days=random.randint(0, 90))

                fields["transaction_date"] = trans_date.strftime("%Y-%m-%d")

    # Write back to file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Randomized dates in {file_path}")
    print(f"   Date range: {start_date.date()} to {end_date.date()}")


# Process fixture files
fixture_files = [
    "t:\\Web Dev\\KinWise\\backend\\fixtures\\comprehensive_test_data.json",
]

for fixture_file in fixture_files:
    if os.path.exists(fixture_file):
        randomize_dates_in_fixture(fixture_file)
    else:
        print(f"❌ File not found: {fixture_file}")

print("\n" + "=" * 80)
print("✅ All fixture dates randomized!")
print("=" * 80)
