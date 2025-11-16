import json

# Load the fixture
with open("fixtures/financial_data.json", "r") as f:
    data = json.load(f)

# Fix each object
for obj in data:
    if "fields" not in obj:
        continue

    fields = obj["fields"]
    model = obj["model"]

    # Goals: rename is_active to status
    if model == "goals.Goal":
        if "is_active" in fields:
            # Convert boolean to status string
            fields["status"] = "active" if fields.pop("is_active") else "inactive"

    # Bills: rename is_paid to status, is_recurring stays
    if model == "bills.Bill":
        if "is_paid" in fields:
            is_paid = fields.pop("is_paid")
            # Set status based on is_paid
            fields["status"] = "paid" if is_paid else "pending"
        # Keep is_recurring as is

        # Rename auto_pay to auto_pay_enabled
        if "auto_pay" in fields:
            fields["auto_pay_enabled"] = fields.pop("auto_pay")

        # Rename reminder_days to reminder_days_before
        if "reminder_days" in fields:
            fields["reminder_days_before"] = fields.pop("reminder_days")

    # Alerts: remove user field (doesn't exist, only household)
    if model == "alerts.Alert":
        if "user" in fields:
            fields.pop("user")
        # Remove created_by field too
        if "created_by" in fields:
            fields.pop("created_by")

    # Rewards: add earned_on field from created_at
    if model == "rewards.Reward":
        if "created_at" in fields and "earned_on" not in fields:
            fields["earned_on"] = fields["created_at"]
        # Remove household field (Reward belongs to user, not household)
        if "household" in fields:
            fields.pop("household")
        # Rename related_transaction to match model
        if "related_transaction" in fields:
            # Model doesn't have this field, remove it
            fields.pop("related_transaction")

# Save fixed fixture
with open("fixtures/financial_data.json", "w") as f:
    json.dump(data, f, indent=2)

print("✅ Fixed financial_data.json")
