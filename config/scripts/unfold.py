# config/settings/base.py
from django.templatetags.static import static

UNFOLD = {
    "SITE_TITLE": "KinWise Admin",
    "SITE_HEADER": "KinWise Family Finance",
    "SITE_URL": "/",
    "SITE_ICON": "/static/icon.svg",
    "DASHBOARD_CALLBACK": None,
    "SHOW_LANGUAGES": False,
    "STYLES": [
        lambda request: static("unfold/css/styles.css"),
        # lambda request: static("admin/custom/unfold-overrides.css"),
    ],
    "SCRIPTS": [
        lambda request: static(
            "admin/js/session-timeout.js"
        ),  # KinWise session timeout
        # if you add custom admin JS later, append more here
        # lambda request: static("admin/custom/unfold-command-disable.js"),
    ],
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Dashboard",
                "separator": True,
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Core Management",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Households",
                        "icon": "home",
                        "link": "/admin/households/household/",
                    },
                    {
                        "title": "Memberships",
                        "icon": "group",
                        "link": "/admin/households/membership/",
                    },
                    {
                        "title": "Organisations",
                        "icon": "business",
                        "link": "/admin/organisations/organisation/",
                    },
                ],
            },
            {
                "title": "Financial Management",
                "separator": True,
                "items": [
                    {
                        "title": "Accounts",
                        "icon": "account_balance",
                        "link": "/admin/accounts/account/",
                    },
                    {
                        "title": "Transactions",
                        "icon": "receipt",
                        "link": "/admin/transactions/transaction/",
                    },
                    {
                        "title": "Transaction Tags",
                        "icon": "label",
                        "link": "/admin/transactions/transactiontag/",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/categories/category/",
                    },
                ],
            },
            {
                "title": "Planning & Goals",
                "separator": True,
                "items": [
                    {
                        "title": "Budgets",
                        "icon": "savings",
                        "link": "/admin/budgets/budget/",
                    },
                    {
                        "title": "Budget Items",
                        "icon": "view_list",
                        "link": "/admin/budgets/budgetitem/",
                    },
                    {
                        "title": "Goals",
                        "icon": "flag",
                        "link": "/admin/goals/goal/",
                    },
                    {
                        "title": "Goal Progress",
                        "icon": "trending_up",
                        "link": "/admin/goals/goalprogress/",
                    },
                    {
                        "title": "Bills",
                        "icon": "payment",
                        "link": "/admin/bills/bill/",
                    },
                ],
            },
            {
                "title": "Gamification & Learning",
                "separator": True,
                "items": [
                    {
                        "title": "Rewards",
                        "icon": "emoji_events",
                        "link": "/admin/rewards/reward/",
                    },
                    {
                        "title": "Financial Lessons",
                        "icon": "school",
                        "link": "/admin/lessons/financiallesson/",
                    },
                ],
            },
            {
                "title": "Alerts & Monitoring",
                "separator": True,
                "items": [
                    {
                        "title": "Alerts",
                        "icon": "notifications_active",
                        "link": "/admin/alerts/alert/",
                    },
                ],
            },
            {
                "title": "System & Security",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Django Admin",
                        "icon": "admin_panel_settings",
                        "link": "/admin/",
                        "badge": "system",
                    },
                ],
            },
        ],
    },
}
