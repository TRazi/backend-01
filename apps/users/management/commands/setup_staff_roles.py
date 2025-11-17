"""
KinWise Staff Roles and Permissions Setup
Implements least-privilege access control for staff members
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create KinWise staff roles with appropriate permissions"

    def handle(self, *args, **options):
        """
        Creates the following staff groups:
        1. Viewer - Can view all data (read-only)
        2. Editor - Can view and edit data (no delete)
        3. Manager - Can view, edit, and delete data
        4. Super Admin - Full access (you only)
        """

        # Get all models we want to control
        models_to_manage = [
            ("transactions", "transaction"),
            ("transactions", "transactionattachment"),
            ("bills", "bill"),
            ("bills", "billattachment"),
            ("accounts", "account"),
            ("households", "household"),
            ("users", "user"),
        ]

        # Get permissions for each model
        permissions_map = {}
        for app_label, model_name in models_to_manage:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            permissions_map[f"{app_label}.{model_name}"] = {
                "view": Permission.objects.get(
                    content_type=content_type, codename=f"view_{model_name}"
                ),
                "add": Permission.objects.get(
                    content_type=content_type, codename=f"add_{model_name}"
                ),
                "change": Permission.objects.get(
                    content_type=content_type, codename=f"change_{model_name}"
                ),
                "delete": Permission.objects.get(
                    content_type=content_type, codename=f"delete_{model_name}"
                ),
            }

        # 1. VIEWER Role - Read-only access
        viewer_group, created = Group.objects.get_or_create(name="KinWise Viewer")
        if created:
            self.stdout.write(
                self.style.SUCCESS("✓ Created 'KinWise Viewer' group")
            )
        else:
            viewer_group.permissions.clear()

        viewer_perms = []
        for model_key, perms in permissions_map.items():
            viewer_perms.append(perms["view"])

        viewer_group.permissions.set(viewer_perms)
        self.stdout.write(f"  - Assigned {len(viewer_perms)} view permissions")

        # 2. EDITOR Role - Can view and edit, but NOT delete
        editor_group, created = Group.objects.get_or_create(name="KinWise Editor")
        if created:
            self.stdout.write(
                self.style.SUCCESS("✓ Created 'KinWise Editor' group")
            )
        else:
            editor_group.permissions.clear()

        editor_perms = []
        for model_key, perms in permissions_map.items():
            editor_perms.extend([perms["view"], perms["add"], perms["change"]])

        editor_group.permissions.set(editor_perms)
        self.stdout.write(f"  - Assigned {len(editor_perms)} permissions (view, add, change)")

        # 3. MANAGER Role - Full CRUD (except users)
        manager_group, created = Group.objects.get_or_create(name="KinWise Manager")
        if created:
            self.stdout.write(
                self.style.SUCCESS("✓ Created 'KinWise Manager' group")
            )
        else:
            manager_group.permissions.clear()

        manager_perms = []
        for model_key, perms in permissions_map.items():
            # Exclude user delete for managers
            if model_key != "users.user":
                manager_perms.extend([
                    perms["view"],
                    perms["add"],
                    perms["change"],
                    perms["delete"],
                ])
            else:
                # Users: can view, add, change, but NOT delete
                manager_perms.extend([
                    perms["view"],
                    perms["add"],
                    perms["change"],
                ])

        manager_group.permissions.set(manager_perms)
        self.stdout.write(f"  - Assigned {len(manager_perms)} permissions (full CRUD, except user delete)")

        self.stdout.write(
            self.style.SUCCESS(
                "\n✓ Staff role setup complete!\n"
                "Available roles:\n"
                "  1. KinWise Viewer  - View-only access\n"
                "  2. KinWise Editor  - View + Edit (no delete)\n"
                "  3. KinWise Manager - Full CRUD (except user deletion)\n\n"
                "To assign a role to a staff member:\n"
                "  1. Go to Admin > Users > Select user\n"
                "  2. Check 'Staff status'\n"
                "  3. In 'Groups' section, select the desired role\n"
                "  4. Save\n"
            )
        )
