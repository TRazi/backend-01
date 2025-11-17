"""
Generate 100 realistic users with complete data across all KinWise models.
Represents real-world usage across all 6 ICPs (Family, DINK, SINK, Student, Individual, Corporate).
"""

import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from users.models import User
from households.models import Household, Membership
from organisations.models import Organisation
from accounts.models import Account
from categories.models import Category
from transactions.models import (
    Transaction,
    TransactionTag,
    TransactionAttachment,
    TransactionSplit,
)
from budgets.models import Budget, BudgetItem
from goals.models import Goal, GoalProgress
from bills.models import Bill
from rewards.models import Reward

# ============================================================================
# DATA POOLS - Realistic New Zealand Data
# ============================================================================

NZ_FIRST_NAMES = [
    "Emma",
    "Olivia",
    "Charlotte",
    "Amelia",
    "Sophie",
    "Isla",
    "Mia",
    "Grace",
    "Chloe",
    "Ruby",
    "Noah",
    "Oliver",
    "Jack",
    "Leo",
    "William",
    "James",
    "Lucas",
    "Thomas",
    "George",
    "Charlie",
    "Aroha",
    "Kahu",
    "Nikau",
    "Aria",
    "Maia",
    "Tane",
    "Wiremu",
    "Anika",
    "Rawiri",
    "Hana",
    "Liam",
    "Ethan",
    "Mason",
    "Logan",
    "Benjamin",
    "Emily",
    "Lily",
    "Harper",
    "Ava",
    "Isabella",
    "Jackson",
    "Hunter",
    "Cooper",
    "Samuel",
    "Daniel",
    "Madison",
    "Ella",
    "Zoe",
    "Scarlett",
    "Hannah",
]

NZ_LAST_NAMES = [
    "Smith",
    "Williams",
    "Brown",
    "Taylor",
    "Davies",
    "Wilson",
    "Evans",
    "Thomas",
    "Roberts",
    "Johnson",
    "Walker",
    "Wright",
    "Robinson",
    "Thompson",
    "White",
    "Hughes",
    "Edwards",
    "Green",
    "Hall",
    "Wood",
    "Harris",
    "Lewis",
    "Martin",
    "Clarke",
    "King",
    "Turner",
    "Cooper",
    "Hill",
    "Moore",
    "Anderson",
    "Te Kanawa",
    "Ngata",
    "Parata",
    "Tamati",
    "Heke",
    "Tui",
    "Rangi",
    "Wiki",
    "Tauroa",
    "Koro",
    "O'Connor",
    "McCarthy",
    "O'Sullivan",
    "Murphy",
    "Kelly",
    "Ryan",
    "Walsh",
    "O'Brien",
    "O'Neill",
    "Quinn",
]

NZ_CITIES = [
    "Auckland",
    "Wellington",
    "Christchurch",
    "Hamilton",
    "Tauranga",
    "Napier",
    "Dunedin",
    "Palmerston North",
    "Rotorua",
    "New Plymouth",
]

HOUSEHOLD_NAMES = [
    "The {last} Family",
    "{last} Household",
    "{first} & {first2}'s Place",
    "{last} & {last2} Family",
    "{first}'s Flat",
    "{city} Flatmates",
    "{last} Whānau",
    "Casa {last}",
    "Chez {last}",
]

# ICP Distribution (Total = 100 users)
ICP_DISTRIBUTION = {
    "family": 30,  # Family ICP - married/partnered with kids
    "dink": 15,  # DINK - dual income no kids
    "sink": 15,  # SINK - single income no kids
    "student": 20,  # Student - flat sharing
    "individual": 15,  # Individual - single person
    "corporate": 5,  # Corporate/Organisation users
}

# Income ranges by ICP (NZD annual)
INCOME_RANGES = {
    "family": (60000, 120000),
    "dink": (100000, 200000),
    "sink": (50000, 100000),
    "student": (15000, 35000),
    "individual": (45000, 90000),
    "corporate": (55000, 110000),
}

# Category templates
CATEGORY_TEMPLATES = {
    "income": [
        "Salary",
        "Bonus",
        "Investment Income",
        "Freelance",
        "Rental Income",
        "Gift Income",
    ],
    "expense": [
        "Groceries",
        "Dining Out",
        "Coffee & Snacks",
        "Transport",
        "Fuel",
        "Public Transport",
        "Rent/Mortgage",
        "Utilities",
        "Internet & Phone",
        "Insurance",
        "Healthcare",
        "Gym",
        "Entertainment",
        "Shopping",
        "Household Items",
        "Pet Care",
        "Kids Activities",
        "Education",
        "Books & Supplies",
        "Gifts",
        "Hobbies",
        "Travel",
        "Parking",
    ],
}

# Transaction descriptions by category
TRANSACTION_DESCRIPTIONS = {
    "Groceries": [
        "Countdown",
        "New World",
        "PAK'nSAVE",
        "FreshChoice",
        "SuperValue",
        "Four Square",
    ],
    "Dining Out": [
        "Hell Pizza",
        "Domino's",
        "McDonald's",
        "KFC",
        "Burger King",
        "Subway",
        "Nando's",
        "Hangi",
        "Local Cafe",
        "Sushi Shop",
    ],
    "Coffee & Snacks": [
        "Starbucks",
        "Muffin Break",
        "Columbus Coffee",
        "Robert Harris",
        "Esquires",
        "Local Bakery",
    ],
    "Transport": ["Uber", "Ola", "Zoomy", "Taxi", "Lime Scooter"],
    "Fuel": ["Z Energy", "BP", "Mobil", "Caltex", "Gull", "NPD"],
    "Utilities": [
        "Contact Energy",
        "Genesis Energy",
        "Mercury Energy",
        "Meridian Energy",
        "Watercare",
    ],
    "Internet & Phone": ["Spark", "Vodafone", "2degrees", "Skinny", "Slingshot"],
    "Entertainment": [
        "Netflix",
        "Spotify",
        "Sky TV",
        "Disney+",
        "Cinema",
        "Event Tickets",
    ],
    "Shopping": [
        "The Warehouse",
        "Kmart",
        "Farmers",
        "Briscoes",
        "Rebel Sport",
        "JB Hi-Fi",
    ],
}

# Goal examples by ICP
GOAL_TEMPLATES = {
    "family": [
        "Emergency Fund",
        "Kids' Education",
        "Family Holiday",
        "New Car",
        "Home Renovation",
        "School Fees",
    ],
    "dink": [
        "Overseas Holiday",
        "House Deposit",
        "New Car",
        "Investment Property",
        "Retirement Fund",
    ],
    "sink": [
        "Emergency Fund",
        "Holiday",
        "New Laptop",
        "Furniture",
        "Career Development",
    ],
    "student": [
        "Books & Supplies",
        "Bond for Flat",
        "Spring Break Trip",
        "New Laptop",
        "Emergency Fund",
    ],
    "individual": [
        "Emergency Fund",
        "Holiday",
        "New Car",
        "Career Course",
        "Home Deposit",
    ],
    "corporate": [
        "Team Building",
        "Conference Budget",
        "Equipment Upgrade",
        "Office Expansion",
    ],
}

# Bill templates
BILL_TEMPLATES = [
    {"name": "Rent", "min": 350, "max": 2500, "frequency": "monthly"},
    {"name": "Power Bill", "min": 80, "max": 350, "frequency": "monthly"},
    {"name": "Internet", "min": 70, "max": 120, "frequency": "monthly"},
    {"name": "Phone Bill", "min": 40, "max": 90, "frequency": "monthly"},
    {"name": "Car Insurance", "min": 60, "max": 150, "frequency": "monthly"},
    {"name": "Gym Membership", "min": 15, "max": 75, "frequency": "monthly"},
    {"name": "Streaming Services", "min": 15, "max": 45, "frequency": "monthly"},
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def random_date_range(start_years_ago=3, end_years_ago=0):
    """Generate random date within range."""
    start = timezone.now() - timedelta(days=365 * start_years_ago)
    end = timezone.now() - timedelta(days=365 * end_years_ago)
    return start + timedelta(days=random.randint(0, int((end - start).days)))


def random_amount(min_val, max_val, decimals=2):
    """Generate random decimal amount."""
    return Decimal(str(round(random.uniform(min_val, max_val), decimals)))


def generate_username(first_name, last_name, existing_usernames):
    """Generate unique username."""
    base = f"{first_name.lower()}.{last_name.lower()}"
    username = base
    counter = 1
    while username in existing_usernames:
        username = f"{base}{counter}"
        counter += 1
    existing_usernames.add(username)
    return username


def generate_email(first_name, last_name, existing_emails):
    """Generate unique email."""
    providers = ["gmail.com", "outlook.com", "xtra.co.nz", "yahoo.com", "hotmail.com"]
    base = f"{first_name.lower()}.{last_name.lower()}"
    email = f"{base}@{random.choice(providers)}"
    counter = 1
    while email in existing_emails:
        email = f"{base}{counter}@{random.choice(providers)}"
        counter += 1
    existing_emails.add(email)
    return email


# ============================================================================
# MAIN GENERATION
# ============================================================================


def main():
    print("=" * 80)
    print("KinWise Realistic User Generation Script")
    print("Generating 100 users across all 6 ICPs with complete data...")
    print("=" * 80)

    # Get existing users count
    existing_count = User.objects.count()
    if existing_count > 0:
        print(f"\n⚠️  WARNING: Database already has {existing_count} users")
        print("This script will create 100 NEW users with unique usernames/emails")
        print("")

    existing_usernames = set(User.objects.values_list("username", flat=True))
    existing_emails = set(User.objects.values_list("email", flat=True))
    users_created = []
    households_created = []
    organisations_created = []

    user_count = 0

    # Create each ICP group
    for icp_type, count in ICP_DISTRIBUTION.items():
        print(f"\n📊 Creating {count} {icp_type.upper()} ICP users...")

        for i in range(count):
            user_count += 1

            # Generate user details
            first_name = random.choice(NZ_FIRST_NAMES)
            last_name = random.choice(NZ_LAST_NAMES)
            username = generate_username(first_name, last_name, existing_usernames)
            email = generate_email(first_name, last_name, existing_emails)
            created_date = random_date_range(3, 0.1)

            # Create user
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=f"+6421{random.randint(1000000, 9999999)}",
                email_verified=random.choice([True, True, True, False]),  # 75% verified
                is_active=True,
                locale="en-nz",
                role=get_role_for_icp(icp_type),
            )
            user.set_password("TestPassword123!")
            user.created_at = created_date
            user.save()
            users_created.append((user, icp_type))

            print(f"  ✓ User {user_count}/100: {user.email} ({icp_type})")

    print(f"\n✅ Created {len(users_created)} users")

    # Create households and populate data
    print("\n" + "=" * 80)
    print("Creating Households, Accounts, Transactions, Budgets, Goals...")
    print("=" * 80)

    household_groups = create_households_by_icp(users_created)

    for household, members, icp_type in household_groups:
        print(f"\n🏠 Populating: {household.name} ({icp_type}, {len(members)} members)")

        # Create accounts
        accounts = create_accounts(household, icp_type)
        print(f"  ✓ {len(accounts)} accounts created")

        # Create categories
        categories = create_categories(household)
        print(f"  ✓ {len(categories)} categories created")

        # Create transactions (last 12-36 months)
        transaction_count = random.randint(150, 500)
        transactions = create_transactions(
            household, accounts, categories, transaction_count, icp_type
        )
        print(f"  ✓ {transaction_count} transactions created")

        # Create budgets
        budgets = create_budgets(household, categories)
        print(f"  ✓ {len(budgets)} budgets created")

        # Create goals
        goals = create_goals(household, icp_type, members)
        print(f"  ✓ {len(goals)} goals created")

        # Create bills
        bills = create_bills(household, accounts, categories, icp_type)
        print(f"  ✓ {len(bills)} bills created")

        # Create rewards for primary user
        if members:
            rewards = create_rewards(members[0], goals, budgets)
            print(f"  ✓ {len(rewards)} rewards created")

    # Create organisations for corporate ICP
    corporate_users = [u for u, icp in users_created if icp == "corporate"]
    if corporate_users:
        print("\n" + "=" * 80)
        print(f"Creating {len(corporate_users)} Organisations...")
        print("=" * 80)

        for corp_user in corporate_users:
            org = create_organisation(corp_user)
            print(f"  ✓ Organisation: {org.name}")

    print("\n" + "=" * 80)
    print("✅ GENERATION COMPLETE!")
    print("=" * 80)
    print(f"📊 Summary:")
    print(f"  - Users: {len(users_created)}")
    print(f"  - Households: {len(household_groups)}")
    print(f"  - Organisations: {len(corporate_users)}")
    print(f"  - Data spans: 2-3 years")
    print(
        f"  - ICPs covered: All 6 (Family, DINK, SINK, Student, Individual, Corporate)"
    )
    print("=" * 80)


# ============================================================================
# ICP-SPECIFIC FUNCTIONS
# ============================================================================


def get_role_for_icp(icp_type):
    """Get appropriate role for ICP type."""
    roles = {
        "family": ["parent", "parent", "admin"],
        "dink": ["admin", "parent"],
        "sink": ["admin"],
        "student": ["flatmate", "observer"],
        "individual": ["admin"],
        "corporate": ["admin"],
    }
    return random.choice(roles[icp_type])


def create_households_by_icp(users_created):
    """Group users into households based on ICP."""
    households = []

    # Family: 2 parents per household
    family_users = [u for u, icp in users_created if icp == "family"]
    for i in range(0, len(family_users), 2):
        members = family_users[i : i + 2]
        if len(members) == 2:
            last_name = members[0].last_name
            household = Household.objects.create(
                name=f"The {last_name} Family",
                household_type="fam",
                budget_cycle="m",
            )
            household.created_at = min(m.created_at for m in members)
            household.save()

            for j, member in enumerate(members):
                Membership.objects.create(
                    user=member,
                    household=household,
                    membership_type="fw",
                    role=["parent", "parent"][j],
                    is_primary=True,
                    status="active",
                )
                member.household = household
                member.save()

            households.append((household, members, "family"))

    # DINK: 2 per household
    dink_users = [u for u, icp in users_created if icp == "dink"]
    for i in range(0, len(dink_users), 2):
        members = dink_users[i : i + 2]
        if len(members) == 2:
            household = Household.objects.create(
                name=f"{members[0].first_name} & {members[1].first_name}'s Place",
                household_type="couple",
                budget_cycle="m",
            )
            household.created_at = min(m.created_at for m in members)
            household.save()

            for member in members:
                Membership.objects.create(
                    user=member,
                    household=household,
                    membership_type="wp",
                    role="admin",
                    is_primary=True,
                    status="active",
                )
                member.household = household
                member.save()

            households.append((household, members, "dink"))

    # SINK: Individual households
    sink_users = [u for u, icp in users_created if icp == "sink"]
    for member in sink_users:
        household = Household.objects.create(
            name=f"{member.last_name} Household",
            household_type="single",
            budget_cycle="m",
        )
        household.created_at = member.created_at
        household.save()

        Membership.objects.create(
            user=member,
            household=household,
            membership_type="if",
            role="admin",
            is_primary=True,
            status="active",
        )
        member.household = household
        member.save()

        households.append((household, [member], "sink"))

    # Students: 3-5 per flat
    student_users = [u for u, icp in users_created if icp == "student"]
    i = 0
    while i < len(student_users):
        remaining = len(student_users) - i
        flat_size = random.randint(min(3, remaining), min(5, remaining))
        members = student_users[i : i + flat_size]
        city = random.choice(NZ_CITIES)

        household = Household.objects.create(
            name=f"{city} Student Flat",
            household_type="student",
            budget_cycle="w",
        )
        household.created_at = min(m.created_at for m in members)
        household.save()

        for j, member in enumerate(members):
            Membership.objects.create(
                user=member,
                household=household,
                membership_type="mm",
                role=["admin", "flatmate"][min(j, 1)],
                is_primary=True,
                status="active",
            )
            member.household = household
            member.save()

        households.append((household, members, "student"))
        i += flat_size

    # Individual: Solo households
    individual_users = [u for u, icp in users_created if icp == "individual"]
    for member in individual_users:
        household = Household.objects.create(
            name=f"{member.first_name}'s Place",
            household_type="single",
            budget_cycle="m",
        )
        household.created_at = member.created_at
        household.save()

        Membership.objects.create(
            user=member,
            household=household,
            membership_type="if",
            role="admin",
            is_primary=True,
            status="active",
        )
        member.household = household
        member.save()

        households.append((household, [member], "individual"))

    # Corporate: Individual households (org membership separate)
    corporate_users = [u for u, icp in users_created if icp == "corporate"]
    for member in corporate_users:
        household = Household.objects.create(
            name=f"{member.last_name} Household",
            household_type="single",
            budget_cycle="m",
        )
        household.created_at = member.created_at
        household.save()

        Membership.objects.create(
            user=member,
            household=household,
            membership_type="if",
            role="admin",
            is_primary=True,
            status="active",
        )
        member.household = household
        member.save()

        households.append((household, [member], "corporate"))

    return households


def create_accounts(household, icp_type):
    """Create realistic accounts for household."""
    accounts = []
    account_types = {
        "family": [
            ("checking", "ANZ Everyday"),
            ("savings", "Emergency Fund"),
            ("credit", "Visa Credit Card"),
        ],
        "dink": [
            ("checking", "BNZ Advantage"),
            ("savings", "House Deposit"),
            ("investment", "Sharesies Portfolio"),
            ("credit", "Amex Platinum"),
        ],
        "sink": [("checking", "Kiwibank Everyday"), ("savings", "Rainy Day Fund")],
        "student": [("checking", "ASB Student Account"), ("savings", "Bond Money")],
        "individual": [("checking", "Westpac Everyday"), ("savings", "Emergency Fund")],
        "corporate": [
            ("checking", "ANZ Business"),
            ("savings", "Tax Reserve"),
            ("credit", "Business Amex"),
        ],
    }

    for acc_type, acc_name in account_types.get(icp_type, []):
        balance = random_amount(500, 15000)
        if acc_type == "credit":
            balance = random_amount(-2000, 0)

        account = Account.objects.create(
            household=household,
            name=acc_name,
            institution=random.choice(["ANZ", "ASB", "BNZ", "Westpac", "Kiwibank"]),
            account_type=acc_type,
            currency="NZD",
            balance=balance,
            include_in_totals=True,
        )
        account.created_at = household.created_at
        account.save()
        accounts.append(account)

    return accounts


def create_categories(household):
    """Create standard categories for household."""
    categories = []

    for cat_name in CATEGORY_TEMPLATES["income"]:
        cat = Category.objects.create(
            household=household,
            name=cat_name,
            category_type="income",
            icon="💰",
            color="#10B981",
            is_active=True,
        )
        categories.append(cat)

    colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6"]
    for cat_name in CATEGORY_TEMPLATES["expense"]:
        cat = Category.objects.create(
            household=household,
            name=cat_name,
            category_type="expense",
            icon="💳",
            color=random.choice(colors),
            is_active=True,
        )
        categories.append(cat)

    return categories


def create_transactions(household, accounts, categories, count, icp_type):
    """Create realistic transactions."""
    transactions = []
    income_range = INCOME_RANGES[icp_type]
    monthly_income = income_range[0] / 12 + random.uniform(
        0, (income_range[1] - income_range[0]) / 12
    )

    # Income transactions (monthly salary)
    income_cats = [c for c in categories if c.category_type == "income"]
    expense_cats = [c for c in categories if c.category_type == "expense"]

    start_date = household.created_at
    end_date = timezone.now()

    # Create monthly income
    current_date = start_date
    while current_date < end_date:
        if accounts and income_cats:
            trans = Transaction.objects.create(
                account=accounts[0],
                transaction_type="income",
                status="completed",
                amount=Decimal(str(round(monthly_income, 2))),
                description="Salary Payment",
                date=current_date,
                category=random.choice(income_cats),
                transaction_source="manual",
            )
            transactions.append(trans)
        current_date += timedelta(days=30)

    # Create expense transactions
    expenses_needed = count - len(transactions)
    for _ in range(expenses_needed):
        if not accounts or not expense_cats:
            break

        category = random.choice(expense_cats)
        trans_date = random_date_range(3, 0)

        # Realistic amounts by category
        amount_ranges = {
            "Groceries": (50, 250),
            "Dining Out": (15, 80),
            "Coffee & Snacks": (5, 25),
            "Rent/Mortgage": (350, 2500),
            "Utilities": (50, 200),
            "Fuel": (60, 120),
            "Entertainment": (20, 100),
            "Shopping": (30, 300),
        }

        min_amt, max_amt = amount_ranges.get(category.name, (10, 100))
        amount = -random_amount(min_amt, max_amt)

        # Get description
        descriptions = TRANSACTION_DESCRIPTIONS.get(category.name, [category.name])
        description = random.choice(descriptions)

        trans = Transaction.objects.create(
            account=random.choice(accounts),
            transaction_type="expense",
            status="completed",
            amount=amount,
            description=description,
            date=trans_date,
            category=category,
            transaction_source=random.choice(["manual", "receipt", "voice"]),
            merchant=description,
        )
        transactions.append(trans)

    return transactions


def create_budgets(household, categories):
    """Create budgets for household."""
    budgets = []
    expense_cats = [c for c in categories if c.category_type == "expense"]

    # Create last 6 months of budgets
    for months_ago in range(6):
        start_date = (
            (timezone.now() - timedelta(days=30 * months_ago)).date().replace(day=1)
        )
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        budget = Budget.objects.create(
            household=household,
            name=f"{start_date.strftime('%B %Y')} Budget",
            start_date=start_date,
            end_date=end_date,
            cycle_type="monthly",
            total_amount=random_amount(2000, 5000),
            status="active" if months_ago == 0 else "completed",
        )
        budgets.append(budget)

    return budgets


def create_goals(household, icp_type, members):
    """Create financial goals."""
    goals = []
    goal_templates = GOAL_TEMPLATES.get(icp_type, ["Savings Goal"])

    for i in range(random.randint(1, 3)):
        goal_name = random.choice(goal_templates)
        target = random_amount(1000, 20000)
        current = random_amount(0, float(target) * 0.7)

        goal = Goal.objects.create(
            household=household,
            name=goal_name,
            goal_type="savings",
            target_amount=target,
            current_amount=current,
            due_date=(timezone.now() + timedelta(days=random.randint(90, 730))).date(),
            status="active",
            milestone_amount=Decimal("500.00"),
            sticker_count=int(current / 500),
        )
        goals.append(goal)

    return goals


def create_bills(household, accounts, categories, icp_type):
    """Create recurring bills."""
    bills = []

    for bill_template in BILL_TEMPLATES[: random.randint(3, 6)]:
        amount = random_amount(bill_template["min"], bill_template["max"])

        bill = Bill.objects.create(
            household=household,
            name=bill_template["name"],
            amount=amount,
            due_date=(timezone.now() + timedelta(days=random.randint(1, 30))).date(),
            frequency=bill_template["frequency"],
            is_recurring=True,
            status=random.choice(["pending", "paid", "pending"]),
            account=random.choice(accounts) if accounts else None,
        )
        bills.append(bill)

    return bills


def create_rewards(user, goals, budgets):
    """Create gamification rewards."""
    rewards = []

    reward_templates = [
        ("first_goal", "First Goal Created", "🎯"),
        ("budget_master", "Budget Master", "📊"),
        ("savings_star", "Savings Star", "⭐"),
        ("streak_7", "7-Day Streak", "🔥"),
    ]

    for reward_type, title, icon in reward_templates[: random.randint(1, 3)]:
        reward = Reward.objects.create(
            user=user,
            reward_type=reward_type,
            title=title,
            description=f"Earned for {title.lower()}",
            icon=icon,
            earned_on=random_date_range(2, 0),
            points=random.randint(10, 100),
        )
        rewards.append(reward)

    return rewards


def create_organisation(owner):
    """Create organisation for corporate user."""
    org_types = ["corp", "edu", "nonprofit", "club"]
    org_names = [
        "TechCorp NZ Ltd",
        "Innovate Solutions",
        "GreenEarth Foundation",
        "Auckland Business Club",
        "Digital Ventures Ltd",
        "Community Trust",
    ]

    org = Organisation.objects.create(
        name=random.choice(org_names),
        organisation_type=random.choice(org_types),
        contact_email=owner.email,
        owner=owner,
        phone_number=f"+6494{random.randint(400000, 999999)}",
        subscription_tier="ww_growth",
        billing_cycle="m",
        subscription_amount=Decimal("99.00"),
        payment_status="active",
        max_members=50,
        is_active=True,
    )

    # Update existing membership to add organisation (rather than creating duplicate)
    membership = Membership.objects.filter(
        user=owner,
        household=owner.household,
    ).first()

    if membership:
        # Update existing membership with organisation
        membership.organisation = org
        membership.membership_type = "ww"
        membership.save()
    else:
        # Create new membership if somehow doesn't exist
        Membership.objects.create(
            user=owner,
            household=owner.household,
            organisation=org,
            membership_type="ww",
            role="admin",
            status="active",
            is_active=True,
        )

    return org


if __name__ == "__main__":
    main()
