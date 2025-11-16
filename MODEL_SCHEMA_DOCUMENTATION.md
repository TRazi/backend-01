# KinWise Backend - Model Schema Documentation
Generated: 2025-11-16 18:56:45
====================================================================================================


####################################################################################################
# APP: ACCOUNTS
####################################################################################################


## Model: Account
**Table:** `accounts`
**Description:** Financial account belonging to a household.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| uuid | UUIDField | ✓ | ✓ | uuid4() | max_length=32, indexed |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| institution | CharField | ✗ | ✗ |  | max_length=255 |
| account_type | CharField | ✓ | ✗ | checking | max_length=20, 6 choices |
| currency | CharField | ✓ | ✗ | NZD | max_length=10 |
| include_in_totals | BooleanField | ✓ | ✗ | True | - |
| balance | DecimalField | ✓ | ✗ | 0 | - |
| available_credit | DecimalField | ✗ | ✗ | - | - |
| credit_limit | DecimalField | ✗ | ✗ | - | - |

### Indexes:

- `uuid`
- `household, account_type`
- `household, include_in_totals`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: ALERTS
####################################################################################################


## Model: Alert
**Table:** `alerts`
**Description:** Represents automated alerts and notifications for a household.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| alert_type | CharField | ✓ | ✗ | - | max_length=30, 9 choices |
| priority | CharField | ✓ | ✗ | medium | max_length=10, 4 choices |
| status | CharField | ✓ | ✗ | active | max_length=20, 3 choices |
| message | TextField | ✓ | ✗ | - | - |
| title | CharField | ✗ | ✗ | - | max_length=255 |
| trigger_value | DecimalField | ✗ | ✗ | - | - |
| related_budget | ForeignKey | ✗ | ✗ | - | → Budget, indexed |
| related_bill | ForeignKey | ✗ | ✗ | - | → Bill, indexed |
| related_account | ForeignKey | ✗ | ✗ | - | → Account, indexed |
| related_goal | ForeignKey | ✗ | ✗ | - | → Goal, indexed |
| action_required | BooleanField | ✓ | ✗ | False | - |
| action_url | CharField | ✗ | ✗ | - | max_length=200 |
| sent_via_email | BooleanField | ✓ | ✗ | False | - |
| sent_via_push | BooleanField | ✓ | ✗ | False | - |
| dismissed_at | DateTimeField | ✗ | ✗ | - | - |
| dismissed_by | ForeignKey | ✗ | ✗ | - | → User, indexed |

### Indexes:

- `household, status, created_at`
- `household, alert_type`
- `status, created_at`
- `priority, status`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: AUDIT
####################################################################################################


## Model: AuditLog
**Table:** `audit_logs`
**Description:** Comprehensive audit trail for all significant system actions.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | ForeignKey | ✗ | ✗ | - | → User, indexed |
| action_type | CharField | ✓ | ✗ | - | max_length=50, 21 choices, indexed |
| action_description | TextField | ✓ | ✗ | - | - |
| object_type | CharField | ✗ | ✗ | - | max_length=100, indexed |
| object_id | PositiveIntegerField | ✗ | ✗ | - | indexed |
| object_repr | CharField | ✗ | ✗ | - | max_length=255 |
| household | ForeignKey | ✗ | ✗ | - | → Household, indexed |
| organisation | ForeignKey | ✗ | ✗ | - | → Organisation, indexed |
| ip_address | GenericIPAddressField | ✗ | ✗ | - | max_length=39 |
| user_agent | TextField | ✗ | ✗ | - | - |
| request_path | CharField | ✗ | ✗ | - | max_length=500 |
| request_method | CharField | ✗ | ✗ | - | max_length=10 |
| changes | JSONField | ✗ | ✗ | dict() | - |
| metadata | JSONField | ✗ | ✗ | dict() | - |
| success | BooleanField | ✓ | ✗ | True | - |
| error_message | TextField | ✗ | ✗ | - | - |

### Indexes:

- `-created_at, user`
- `action_type, -created_at`
- `household, -created_at`
- `object_type, object_id`
- `ip_address, -created_at`

----------------------------------------------------------------------------------------------------

## Model: FailedLoginAttempt
**Table:** `failed_login_attempts`
**Description:** Track failed login attempts for security analysis.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| username | CharField | ✓ | ✗ | - | max_length=255, indexed |
| ip_address | GenericIPAddressField | ✓ | ✗ | - | max_length=39, indexed |
| user_agent | TextField | ✗ | ✗ | - | - |
| request_path | CharField | ✗ | ✗ | - | max_length=500 |
| attempt_count | PositiveIntegerField | ✓ | ✗ | 1 | - |
| locked_out | BooleanField | ✓ | ✗ | False | - |
| resolved | BooleanField | ✓ | ✗ | False | - |
| resolved_by | ForeignKey | ✗ | ✗ | - | → User, indexed |
| notes | TextField | ✗ | ✗ | - | - |

### Indexes:

- `-created_at, ip_address`
- `username, -created_at`
- `resolved, -created_at`

----------------------------------------------------------------------------------------------------

## Model: DataExportLog
**Table:** `data_export_logs`
**Description:** Track all data exports for compliance and security.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | ForeignKey | ✗ | ✗ | - | → User, indexed |
| export_type | CharField | ✓ | ✗ | - | max_length=50, 5 choices, indexed |
| household | ForeignKey | ✗ | ✗ | - | → Household, indexed |
| record_count | PositiveIntegerField | ✓ | ✗ | - | - |
| date_range_start | DateField | ✗ | ✗ | - | - |
| date_range_end | DateField | ✗ | ✗ | - | - |
| ip_address | GenericIPAddressField | ✓ | ✗ | - | max_length=39 |
| user_agent | TextField | ✗ | ✗ | - | - |
| file_format | CharField | ✓ | ✗ | json | max_length=20 |
| file_size_bytes | PositiveIntegerField | ✗ | ✗ | - | - |
| export_filters | JSONField | ✗ | ✗ | dict() | - |

### Indexes:

- `-created_at, user`
- `export_type, -created_at`
- `household, -created_at`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: BILLS
####################################################################################################


## Model: Bill
**Table:** `bills`
**Description:** Represents a bill or recurring payment for a household.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| description | TextField | ✗ | ✗ | - | - |
| amount | DecimalField | ✓ | ✗ | - | - |
| due_date | DateField | ✓ | ✗ | - | - |
| frequency | CharField | ✓ | ✗ | monthly | max_length=20, 6 choices |
| is_recurring | BooleanField | ✓ | ✗ | True | - |
| status | CharField | ✓ | ✗ | pending | max_length=20, 4 choices |
| paid_date | DateField | ✗ | ✗ | - | - |
| transaction | ForeignKey | ✗ | ✗ | - | → Transaction, indexed |
| category | ForeignKey | ✗ | ✗ | - | → Category, indexed |
| account | ForeignKey | ✗ | ✗ | - | → Account, indexed |
| reminder_days_before | PositiveIntegerField | ✓ | ✗ | 3 | - |
| auto_pay_enabled | BooleanField | ✓ | ✗ | False | - |
| color | CharField | ✓ | ✗ | #EF4444 | max_length=7 |
| notes | TextField | ✗ | ✗ | - | - |
| next_bill | ForeignKey | ✗ | ✗ | - | → Bill, indexed |

### Indexes:

- `household, due_date`
- `household, status`
- `status, due_date`
- `due_date`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: BUDGETS
####################################################################################################


## Model: Budget
**Table:** `budgets`
**Description:** Represents a budget period for a household.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| start_date | DateField | ✓ | ✗ | - | - |
| end_date | DateField | ✓ | ✗ | - | - |
| cycle_type | CharField | ✓ | ✗ | monthly | max_length=20, 6 choices |
| total_amount | DecimalField | ✓ | ✗ | - | - |
| status | CharField | ✓ | ✗ | active | max_length=20, 4 choices |
| alert_threshold | DecimalField | ✓ | ✗ | 80.0 | - |
| rollover_enabled | BooleanField | ✓ | ✗ | False | - |
| notes | TextField | ✗ | ✗ | - | - |

### Indexes:

- `household, start_date, end_date`
- `household, status`
- `start_date, end_date`

----------------------------------------------------------------------------------------------------

## Model: BudgetItem
**Table:** `budget_items`
**Description:** Represents a category-specific budget allocation within a Budget.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| budget | ForeignKey | ✓ | ✗ | - | → Budget, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| amount | DecimalField | ✓ | ✗ | - | - |
| category | ForeignKey | ✗ | ✗ | - | → Category, indexed |
| notes | TextField | ✗ | ✗ | - | - |

### Indexes:

- `budget, category`

### Unique Together:

- `budget, name`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: CATEGORIES
####################################################################################################


## Model: Category
**Table:** `categories`
**Description:** Represents a transaction category for organizing and reporting.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✗ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=100 |
| description | TextField | ✗ | ✗ | - | - |
| category_type | CharField | ✓ | ✗ | expense | max_length=10, 3 choices |
| parent | ForeignKey | ✗ | ✗ | - | → Category, indexed |
| icon | CharField | ✗ | ✗ | - | max_length=50 |
| color | CharField | ✓ | ✗ | #6B7280 | max_length=7 |
| display_order | PositiveIntegerField | ✓ | ✗ | 0 | - |
| is_active | BooleanField | ✓ | ✗ | True | - |
| is_deleted | BooleanField | ✓ | ✗ | False | - |
| is_system | BooleanField | ✓ | ✗ | False | - |
| is_budgetable | BooleanField | ✓ | ✗ | True | - |

### Indexes:

- `household, is_active, is_deleted`
- `household, category_type, is_deleted`
- `parent`
- `is_system`

### Unique Together:

- `household, name, is_deleted`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: COMMON
####################################################################################################


####################################################################################################
# APP: GOALS
####################################################################################################


## Model: Goal
**Table:** `goals`
**Description:** Represents a savings or financial goal for a household.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| description | TextField | ✗ | ✗ | - | - |
| goal_type | CharField | ✓ | ✗ | savings | max_length=20, 6 choices |
| target_amount | DecimalField | ✓ | ✗ | - | - |
| current_amount | DecimalField | ✓ | ✗ | 0.0 | - |
| due_date | DateField | ✓ | ✗ | - | - |
| status | CharField | ✓ | ✗ | active | max_length=20, 4 choices |
| milestone_amount | DecimalField | ✗ | ✗ | - | - |
| sticker_count | PositiveIntegerField | ✓ | ✗ | 0 | - |
| auto_contribute | BooleanField | ✓ | ✗ | False | - |
| contribution_percentage | DecimalField | ✗ | ✗ | - | - |
| icon | CharField | ✗ | ✗ | - | max_length=50 |
| color | CharField | ✓ | ✗ | #10B981 | max_length=7 |
| image | FileField | ✗ | ✗ | - | max_length=100 |

### Indexes:

- `household, status`
- `household, due_date`
- `status, due_date`

----------------------------------------------------------------------------------------------------

## Model: GoalProgress
**Table:** `goal_progress`
**Description:** Tracks individual contributions/progress updates to a goal.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| goal | ForeignKey | ✓ | ✗ | - | → Goal, indexed |
| amount_added | DecimalField | ✓ | ✗ | - | - |
| date_added | DateTimeField | ✓ | ✗ | now() | - |
| transaction | ForeignKey | ✗ | ✗ | - | → Transaction, indexed |
| notes | TextField | ✗ | ✗ | - | - |
| milestone_reached | BooleanField | ✓ | ✗ | False | - |

### Indexes:

- `goal, date_added`
- `date_added`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: HOUSEHOLDS
####################################################################################################


## Model: Household
**Table:** `households`
**Description:** Represents a household - the main tenant unit in the system.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| uuid | UUIDField | ✓ | ✓ | uuid4() | max_length=32, indexed |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| household_type | CharField | ✓ | ✗ | fam | max_length=10, 7 choices |
| budget_cycle | CharField | ✓ | ✗ | m | max_length=1, 5 choices |

### Indexes:

- `uuid`

----------------------------------------------------------------------------------------------------

## Model: Membership
**Table:** `memberships`
**Description:** Links users to households/organisations with subscription and permission details.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | ForeignKey | ✓ | ✗ | - | → User, indexed |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| organisation | ForeignKey | ✗ | ✗ | - | → Organisation, indexed |
| membership_type | CharField | ✓ | ✗ | sw | max_length=2, 6 choices |
| role | CharField | ✓ | ✗ | observer | max_length=20, 6 choices |
| status | CharField | ✓ | ✗ | active | max_length=20, 5 choices |
| is_active | BooleanField | ✓ | ✗ | True | - |
| start_date | DateTimeField | ✗ | ✗ | - | - |
| ended_at | DateTimeField | ✗ | ✗ | - | - |
| is_primary | BooleanField | ✓ | ✗ | False | - |
| billing_cycle | CharField | ✗ | ✗ | - | max_length=1, 5 choices |
| next_billing_date | DateField | ✗ | ✗ | - | - |
| amount | DecimalField | ✗ | ✗ | - | - |
| payment_status | CharField | ✗ | ✗ | - | max_length=20, 4 choices |

### Indexes:

- `user, is_active`
- `household, is_active`
- `user, is_primary`
- `is_active, ended_at`

### Unique Together:

- `user, household`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: LESSONS
####################################################################################################


## Model: FinancialLesson
**Table:** `financial_lessons`
**Description:** Represents educational financial literacy content.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| title | CharField | ✓ | ✗ | - | max_length=255 |
| content | TextField | ✓ | ✗ | - | - |
| age_group | CharField | ✓ | ✗ | all | max_length=20, 5 choices |
| difficulty | CharField | ✓ | ✗ | beginner | max_length=20, 3 choices |
| category | CharField | ✗ | ✗ | - | max_length=100 |
| display_order | PositiveIntegerField | ✓ | ✗ | 0 | - |
| image | FileField | ✗ | ✗ | - | max_length=100 |
| video_url | CharField | ✗ | ✗ | - | max_length=200 |
| estimated_duration | PositiveIntegerField | ✓ | ✗ | 5 | - |
| is_published | BooleanField | ✓ | ✗ | False | - |
| summary | TextField | ✗ | ✗ | - | - |
| tags | CharField | ✗ | ✗ | - | max_length=255 |

### Indexes:

- `age_group, is_published`
- `category, display_order`
- `is_published, display_order`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: ORGANISATIONS
####################################################################################################


## Model: Organisation
**Table:** `organisations`
**Description:** Represents an organisation for 'Whānau Works' memberships.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| name | CharField | ✓ | ✗ | - | max_length=255 |
| organisation_type | CharField | ✓ | ✗ | corp | max_length=10, 6 choices |
| contact_email | CharField | ✓ | ✗ | - | max_length=254 |
| owner | ForeignKey | ✓ | ✗ | - | → User, indexed |
| phone_number | CharField | ✗ | ✗ | - | max_length=17 |
| address | TextField | ✗ | ✗ | - | - |
| website | CharField | ✗ | ✗ | - | max_length=200 |
| default_budget_cycle | CharField | ✓ | ✗ | m | max_length=1, 3 choices |
| currency | CharField | ✓ | ✗ | NZD | max_length=3, 5 choices |
| financial_year_start | CharField | ✓ | ✗ | 01-01 | max_length=5 |
| subscription_tier | CharField | ✓ | ✗ | ww_starter | max_length=20, 3 choices |
| billing_cycle | CharField | ✓ | ✗ | m | max_length=1, 3 choices |
| next_billing_date | DateField | ✗ | ✗ | - | - |
| subscription_amount | DecimalField | ✓ | ✗ | 0.0 | - |
| payment_status | CharField | ✓ | ✗ | trial | max_length=20, 4 choices |
| is_active | BooleanField | ✓ | ✗ | True | - |
| max_members | PositiveIntegerField | ✓ | ✗ | 50 | - |

### Indexes:

- `name`
- `is_active, payment_status`
- `owner`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: PRIVACY
####################################################################################################


####################################################################################################
# APP: REPORTS
####################################################################################################


####################################################################################################
# APP: REWARDS
####################################################################################################


## Model: Reward
**Table:** `rewards`
**Description:** Represents gamification rewards earned by users.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | ForeignKey | ✓ | ✗ | - | → User, indexed |
| reward_type | CharField | ✓ | ✗ | - | max_length=30, 10 choices |
| title | CharField | ✓ | ✗ | - | max_length=255 |
| description | TextField | ✗ | ✗ | - | - |
| icon | CharField | ✗ | ✗ | - | max_length=50 |
| badge_image | FileField | ✗ | ✗ | - | max_length=100 |
| earned_on | DateTimeField | ✓ | ✗ | - | - |
| points | PositiveIntegerField | ✓ | ✗ | 0 | - |
| related_goal | ForeignKey | ✗ | ✗ | - | → Goal, indexed |
| related_budget | ForeignKey | ✗ | ✗ | - | → Budget, indexed |
| is_visible | BooleanField | ✓ | ✗ | True | - |

### Indexes:

- `user, earned_on`
- `user, reward_type`
- `earned_on`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: TRANSACTIONS
####################################################################################################


## Model: Transaction
**Table:** `transactions`
**Description:** Represents a financial transaction (income, expense, or transfer).

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| uuid | UUIDField | ✓ | ✓ | uuid4() | max_length=32, indexed |
| account | ForeignKey | ✓ | ✗ | - | → Account, indexed |
| goal | ForeignKey | ✗ | ✗ | - | → Goal, indexed |
| budget | ForeignKey | ✗ | ✗ | - | → Budget, indexed |
| transaction_type | CharField | ✓ | ✗ | - | max_length=20, 3 choices |
| status | CharField | ✓ | ✗ | completed | max_length=20, 4 choices |
| amount | DecimalField | ✓ | ✗ | - | - |
| description | CharField | ✓ | ✗ | - | max_length=500 |
| date | DateTimeField | ✓ | ✗ | - | - |
| category | ForeignKey | ✗ | ✗ | - | → Category, indexed |
| receipt_image | FileField | ✗ | ✗ | - | max_length=100 |
| voice_entry_flag | BooleanField | ✓ | ✗ | False | - |
| transaction_source | CharField | ✓ | ✗ | manual | max_length=20, 4 choices |
| merchant | CharField | ✗ | ✗ | - | max_length=255 |
| notes | TextField | ✗ | ✗ | - | - |
| is_recurring | BooleanField | ✓ | ✗ | False | - |
| linked_transaction | ForeignKey | ✗ | ✗ | - | → Transaction, indexed |
| tags | ManyToManyField | ✗ | ✗ | - | → TransactionTag |

### Indexes:

- `uuid`
- `account, date`
- `category, date`
- `transaction_type, status, date`
- `date`
- `account, -date`
- `status, date`

----------------------------------------------------------------------------------------------------

## Model: TransactionTag
**Table:** `transaction_tags`
**Description:** Tags for flexible, multi-dimensional transaction categorization.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| household | ForeignKey | ✓ | ✗ | - | → Household, indexed |
| name | CharField | ✓ | ✗ | - | max_length=50 |
| color | CharField | ✓ | ✗ | #6B7280 | max_length=7 |
| description | TextField | ✗ | ✗ | - | - |

### Unique Together:

- `household, name`

----------------------------------------------------------------------------------------------------

####################################################################################################
# APP: USERS
####################################################################################################


## Model: User
**Table:** `users`
**Description:** Custom user model using email as the unique identifier.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| password | CharField | ✓ | ✗ | - | max_length=128 |
| last_login | DateTimeField | ✗ | ✗ | - | - |
| is_superuser | BooleanField | ✓ | ✗ | False | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| uuid | UUIDField | ✓ | ✓ | uuid4() | max_length=32, indexed |
| username | CharField | ✗ | ✓ | - | max_length=150, indexed |
| email | CharField | ✓ | ✓ | - | max_length=254, indexed |
| email_verified | BooleanField | ✓ | ✗ | False | - |
| first_name | CharField | ✗ | ✗ | - | max_length=150 |
| last_name | CharField | ✗ | ✗ | - | max_length=150 |
| phone_number | CharField | ✗ | ✗ | - | max_length=17 |
| is_active | BooleanField | ✓ | ✗ | True | - |
| is_staff | BooleanField | ✓ | ✗ | False | - |
| locale | CharField | ✓ | ✗ | en-nz | max_length=10, 5 choices |
| role | CharField | ✓ | ✗ | observer | max_length=20, 6 choices |
| household | ForeignKey | ✗ | ✗ | - | → Household, indexed |
| groups | ManyToManyField | ✗ | ✗ | - | → Group |
| user_permissions | ManyToManyField | ✗ | ✗ | - | → Permission |

### Indexes:

- `email, is_active`
- `username, is_active`
- `uuid`

----------------------------------------------------------------------------------------------------

## Model: UserMFADevice
**Table:** `users_usermfadevice`
**Description:** UserMFADevice(id, created_at, updated_at, user, secret_key, is_enabled, backup_codes, last_used_at)

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | OneToOneField | ✓ | ✓ | - | → User, indexed |
| secret_key | CharField | ✓ | ✗ | - | max_length=64 |
| is_enabled | BooleanField | ✓ | ✗ | False | - |
| backup_codes | JSONField | ✗ | ✗ | list() | - |
| last_used_at | DateTimeField | ✗ | ✗ | - | - |

----------------------------------------------------------------------------------------------------

## Model: EmailOTP
**Table:** `email_otp`
**Description:** One-Time Password for passwordless email login.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | ForeignKey | ✓ | ✗ | - | → User, indexed |
| code | CharField | ✓ | ✗ | - | max_length=6 |
| expires_at | DateTimeField | ✓ | ✗ | - | - |
| is_used | BooleanField | ✓ | ✗ | False | indexed |
| ip_address | GenericIPAddressField | ✗ | ✗ | - | max_length=39 |

### Indexes:

- `user, -created_at`
- `code, is_used`
- `expires_at, is_used`

----------------------------------------------------------------------------------------------------

## Model: EmailVerification
**Table:** `email_verification`
**Description:** Email verification token for new user registration.

### Fields:

| Field Name | Type | Required | Unique | Default | Notes |
|------------|------|----------|--------|---------|-------|
| id | BigAutoField | ✗ | ✓ | - | - |
| created_at | DateTimeField | ✓ | ✗ | now() | indexed |
| updated_at | DateTimeField | ✗ | ✗ | - | - |
| user | OneToOneField | ✓ | ✓ | - | → User, indexed |
| token | UUIDField | ✓ | ✓ | uuid4() | max_length=32, indexed |
| verified_at | DateTimeField | ✗ | ✗ | - | - |

### Indexes:

- `token`
- `user, verified_at`

----------------------------------------------------------------------------------------------------
