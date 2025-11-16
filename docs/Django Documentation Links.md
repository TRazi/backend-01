

### Django Documentation


***

#### First steps

make sure that you factor in this styleguide in collaboration with the Django docs

url: https://github.com/HackSoftware/Django-Styleguide 


- [intro/overview/](intro/overview/) - Overview
- [intro/install/](intro/install/) - Installation

**Tutorial:**

- [intro/tutorial01/](intro/tutorial01/) - Part 1: Requests and responses
- [intro/tutorial02/](intro/tutorial02/) - Part 2: Models and the admin site
- [intro/tutorial03/](intro/tutorial03/) - Part 3: Views and templates
- [intro/tutorial04/](intro/tutorial04/) - Part 4: Forms and generic views
- [intro/tutorial05/](intro/tutorial05/) - Part 5: Testing
- [intro/tutorial06/](intro/tutorial06/) - Part 6: Static files
- [intro/tutorial07/](intro/tutorial07/) - Part 7: Customizing the admin site
- [intro/tutorial08/](intro/tutorial08/) - Part 8: Adding third-party packages

**Advanced Tutorials:**

- [intro/reusable-apps/](intro/reusable-apps/) - How to write reusable apps
- [intro/contributing/](intro/contributing/) - Writing your first contribution to Django

***

#### Getting help

- [faq/](faq/) - FAQ
- [genindex/](genindex/) - Index
- [py-modindex/](py-modindex/) - Module Index
- [contents/](contents/) - Detailed table of contents
- [faq/help/](faq/help/) - FAQ: Getting Help
- [https://code.djangoproject.com/](https://code.djangoproject.com/) - Ticket tracker

***

#### How the documentation is organized

- [intro/](intro/) - Tutorials
- [topics/](topics/) - Topic guides
- [ref/](ref/) - Reference guides
- [howto/](howto/) - How-to guides

***

#### The model layer

**Models:**

- [topics/db/models/](topics/db/models/) - Introduction to models
- [ref/models/fields/](ref/models/fields/) - Field types
- [ref/models/indexes/](ref/models/indexes/) - Indexes
- [ref/models/options/](ref/models/options/) - Meta options
- [ref/models/class/](ref/models/class/) - Model class

**QuerySets:**

- [topics/db/queries/](topics/db/queries/) - Making queries
- [ref/models/querysets/](ref/models/querysets/) - QuerySet method reference
- [ref/models/lookups/](ref/models/lookups/) - Lookup expressions

**Model instances:**

- [ref/models/instances/](ref/models/instances/) - Instance methods
- [ref/models/relations/](ref/models/relations/) - Accessing related objects

**Migrations:**

- [topics/migrations/](topics/migrations/) - Introduction to Migrations
- [ref/migration-operations/](ref/migration-operations/) - Operations reference
- [ref/schema-editor/](ref/schema-editor/) - SchemaEditor
- [howto/writing-migrations/](howto/writing-migrations/) - Writing migrations

**Advanced:**

- [topics/db/managers/](topics/db/managers/) - Managers
- [topics/db/sql/](topics/db/sql/) - Raw SQL
- [topics/db/transactions/](topics/db/transactions/) - Transactions
- [topics/db/aggregation/](topics/db/aggregation/) - Aggregation
- [topics/db/search/](topics/db/search/) - Search
- [howto/custom-model-fields/](howto/custom-model-fields/) - Custom fields
- [topics/db/multi-db/](topics/db/multi-db/) - Multiple databases
- [howto/custom-lookups/](howto/custom-lookups/) - Custom lookups
- [ref/models/expressions/](ref/models/expressions/) - Query Expressions
- [ref/models/conditional-expressions/](ref/models/conditional-expressions/) - Conditional Expressions
- [ref/models/database-functions/](ref/models/database-functions/) - Database Functions

**Other:**

- [ref/databases/](ref/databases/) - Supported databases
- [howto/legacy-databases/](howto/legacy-databases/) - Legacy databases
- [howto/initial-data/](howto/initial-data/) - Providing initial data
- [topics/db/optimization/](topics/db/optimization/) - Optimize database access
- [ref/contrib/postgres/](ref/contrib/postgres/) - PostgreSQL specific features

***

#### The view layer

**The basics:**

- [topics/http/urls/](topics/http/urls/) - URLconfs
- [topics/http/views/](topics/http/views/) - View functions
- [topics/http/shortcuts/](topics/http/shortcuts/) - Shortcuts
- [topics/http/decorators/](topics/http/decorators/) - Decorators
- [topics/async/](topics/async/) - Asynchronous Support

**Reference:**

- [ref/views/](ref/views/) - Built-in Views
- [ref/request-response/](ref/request-response/) - Request/response objects
- [ref/template-response/](ref/template-response/) - TemplateResponse objects

**File uploads:**

- [topics/http/file-uploads/](topics/http/file-uploads/) - Overview
- [ref/files/file/](ref/files/file/) - File objects
- [ref/files/storage/](ref/files/storage/) - Storage API
- [topics/files/](topics/files/) - Managing files
- [howto/custom-file-storage/](howto/custom-file-storage/) - Custom storage

**Class-based views:**

- [topics/class-based-views/](topics/class-based-views/) - Overview
- [topics/class-based-views/generic-display/](topics/class-based-views/generic-display/) - Built-in display views
- [topics/class-based-views/generic-editing/](topics/class-based-views/generic-editing/) - Built-in editing views
- [topics/class-based-views/mixins/](topics/class-based-views/mixins/) - Using mixins
- [ref/class-based-views/](ref/class-based-views/) - API reference
- [ref/class-based-views/flattened-index/](ref/class-based-views/flattened-index/) - Flattened index

**Advanced:**

- [howto/outputting-csv/](howto/outputting-csv/) - Generating CSV
- [howto/outputting-pdf/](howto/outputting-pdf/) - Generating PDF

**Middleware:**

- [topics/http/middleware/](topics/http/middleware/) - Overview
- [ref/middleware/](ref/middleware/) - Built-in middleware classes

***

#### The template layer

**The basics:**

- [topics/templates/](topics/templates/) - Overview

**For designers:**

- [ref/templates/language/](ref/templates/language/) - Language overview
- [ref/templates/builtins/](ref/templates/builtins/) - Built-in tags and filters
- [ref/contrib/humanize/](ref/contrib/humanize/) - Humanization

**For programmers:**

- [ref/templates/api/](ref/templates/api/) - Template API
- [howto/custom-template-tags/](howto/custom-template-tags/) - Custom tags and filters
- [howto/custom-template-backend/](howto/custom-template-backend/) - Custom template backend

***

#### Forms

**The basics:**

- [topics/forms/](topics/forms/) - Overview
- [ref/forms/api/](ref/forms/api/) - Form API
- [ref/forms/fields/](ref/forms/fields/) - Built-in fields
- [ref/forms/widgets/](ref/forms/widgets/) - Built-in widgets

**Advanced:**

- [topics/forms/modelforms/](topics/forms/modelforms/) - Forms for models
- [topics/forms/media/](topics/forms/media/) - Integrating media
- [topics/forms/formsets/](topics/forms/formsets/) - Formsets
- [ref/forms/validation/](ref/forms/validation/) - Customizing validation

***

#### The development process

**Settings:**

- [topics/settings/](topics/settings/) - Overview
- [ref/settings/](ref/settings/) - Full list of settings

**Applications:**

- [ref/applications/](ref/applications/) - Overview

**Exceptions:**

- [ref/exceptions/](ref/exceptions/) - Overview

**django-admin and manage.py:**

- [ref/django-admin/](ref/django-admin/) - Overview
- [howto/custom-management-commands/](howto/custom-management-commands/) - Adding custom commands

**Testing:**

- [topics/testing/](topics/testing/) - Introduction
- [topics/testing/overview/](topics/testing/overview/) - Writing and running tests
- [topics/testing/tools/](topics/testing/tools/) - Included testing tools
- [topics/testing/advanced/](topics/testing/advanced/) - Advanced topics

**Deployment:**

- [howto/deployment/](howto/deployment/) - Overview
- [howto/deployment/wsgi/](howto/deployment/wsgi/) - WSGI servers
- [howto/deployment/asgi/](howto/deployment/asgi/) - ASGI servers
- [howto/static-files/deployment/](howto/static-files/deployment/) - Deploying static files
- [howto/error-reporting/](howto/error-reporting/) - Tracking code errors by email
- [howto/deployment/checklist/](howto/deployment/checklist/) - Deployment checklist

***

#### The admin

- [ref/contrib/admin/](ref/contrib/admin/) - Admin site
- [ref/contrib/admin/actions/](ref/contrib/admin/actions/) - Admin actions
- [ref/contrib/admin/admindocs/](ref/contrib/admin/admindocs/) - Admin documentation generator

***

#### Security

- [topics/security/](topics/security/) - Security overview
- [releases/security/](releases/security/) - Disclosed security issues in Django
- [ref/clickjacking/](ref/clickjacking/) - Clickjacking protection
- [ref/csrf/](ref/csrf/) - Cross Site Request Forgery protection
- [topics/signing/](topics/signing/) - Cryptographic signing
- [ref/middleware/\#security-middleware](ref/middleware/#security-middleware) - Security Middleware

***

#### Internationalization and localization

- [topics/i18n/](topics/i18n/) - Overview
- [topics/i18n/translation/](topics/i18n/translation/) - Internationalization
- [topics/i18n/translation/\#how-to-create-language-files](topics/i18n/translation/#how-to-create-language-files) - Localization
- [topics/i18n/formatting/](topics/i18n/formatting/) - Localized web UI formatting and form input
- [topics/i18n/timezones/](topics/i18n/timezones/) - Time zones

***

#### Performance and optimization

- [topics/performance/](topics/performance/) - Performance and optimization overview

***

#### Geographic framework

- [ref/contrib/gis/](ref/contrib/gis/) - GeoDjango

***

#### Common web application tools

**Authentication:**

- [topics/auth/](topics/auth/) - Overview
- [topics/auth/default/](topics/auth/default/) - Using the authentication system
- [topics/auth/passwords/](topics/auth/passwords/) - Password management
- [topics/auth/customizing/](topics/auth/customizing/) - Customizing authentication
- [ref/contrib/auth/](ref/contrib/auth/) - API Reference
- [topics/cache/](topics/cache/) - Caching
- [topics/logging/](topics/logging/) - Logging
- [topics/email/](topics/email/) - Sending emails
- [ref/contrib/syndication/](ref/contrib/syndication/) - Syndication feeds (RSS/Atom)
- [topics/pagination/](topics/pagination/) - Pagination
- [ref/contrib/messages/](ref/contrib/messages/) - Messages framework
- [topics/serialization/](topics/serialization/) - Serialization
- [topics/http/sessions/](topics/http/sessions/) - Sessions
- [ref/contrib/sitemaps/](ref/contrib/sitemaps/) - Sitemaps
- [ref/contrib/staticfiles/](ref/contrib/staticfiles/) - Static files management
- [ref/validators/](ref/validators/) - Data validation

***

#### Other core functionalities

- [topics/conditional-view-processing/](topics/conditional-view-processing/) - Conditional content processing
- [ref/contrib/contenttypes/](ref/contrib/contenttypes/) - Content types and generic relations
- [ref/contrib/flatpages/](ref/contrib/flatpages/) - Flatpages
- [ref/contrib/redirects/](ref/contrib/redirects/) - Redirects
- [topics/signals/](topics/signals/) - Signals
- [topics/checks/](topics/checks/) - System check framework
- [ref/contrib/sites/](ref/contrib/sites/) - The sites framework
- [ref/unicode/](ref/unicode/) - Unicode in Django

***

#### The Django open-source project

**Community:**

- [internals/contributing/](internals/contributing/) - Contributing to Django
- [internals/release-process/](internals/release-process/) - The release process
- [internals/organization/](internals/organization/) - Team organization
- [internals/git/](internals/git/) - The Django source code repository
- [internals/security/](internals/security/) - Security policies
- [internals/mailing-lists/](internals/mailing-lists/) - Mailing lists and Forum

**Design philosophies:**

- [misc/design-philosophies/](misc/design-philosophies/) - Overview

**Documentation:**

- [internals/contributing/writing-documentation/](internals/contributing/writing-documentation/) - About this documentation

**Third-party distributions:**

- [misc/distributions/](misc/distributions/) - Overview

**Django over time:**

- [misc/api-stability/](misc/api-stability/) - API stability
- [releases/](releases/) - Release notes and upgrading instructions
- [internals/deprecation/](internals/deprecation/) - Deprecation Timeline

