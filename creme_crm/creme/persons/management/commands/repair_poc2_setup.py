from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from creme.creme_core.models import MenuConfigItem
from creme.persons.models import Contact


class Command(BaseCommand):
    help = (
        "Répare la configuration POC 2 locale : "
        "entrées de menu Annuaire, utilisateur admin, "
        "et détachement du contact Fulbert CREME."
    )

    DIRECTORY_LABELS = {"Annuaire", "Directory"}
    MENU_ENTRIES = (
        ("persons-mass-emailing", 40),
        ("persons-taxe", 50),
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afficher les actions sans modifier la base.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        actions = []

        with transaction.atomic():
            directory_item = self._get_directory_menu()
            actions.extend(self._ensure_menu_entries(directory_item, dry_run=dry_run))
            actions.extend(self._repair_admin_user(dry_run=dry_run))
            actions.extend(self._detach_fulbert(dry_run=dry_run))

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Résumé de repair_poc2_setup"))
        for action in actions:
            self.stdout.write(f"- {action}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Mode dry-run : aucune modification n'a été enregistrée."))

    def _get_directory_menu(self):
        root_items = MenuConfigItem.objects.filter(
            parent=None,
            entry_id="creme_core-container",
            role=None,
            superuser=False,
        ).order_by("order", "id")

        for item in root_items:
            label = (item.entry_data or {}).get("label")
            if label in self.DIRECTORY_LABELS:
                return item

        raise CommandError(
            "Impossible de trouver le menu racine 'Annuaire'/'Directory' "
            "dans MenuConfigItem."
        )

    def _ensure_menu_entries(self, directory_item, dry_run=False):
        actions = []

        for entry_id, order in self.MENU_ENTRIES:
            existing = MenuConfigItem.objects.filter(
                parent=directory_item,
                entry_id=entry_id,
                role=None,
                superuser=False,
            ).first()

            if existing is not None:
                changed = False

                if existing.order != order:
                    existing.order = order
                    changed = True

                if changed and not dry_run:
                    existing.save(update_fields=["order"])

                if changed:
                    actions.append(
                        f"Entrée de menu '{entry_id}' déjà présente, ordre corrigé à {order}."
                    )
                else:
                    actions.append(
                        f"Entrée de menu '{entry_id}' déjà présente sous Annuaire."
                    )
                continue

            if not dry_run:
                MenuConfigItem.objects.create(
                    entry_id=entry_id,
                    order=order,
                    parent=directory_item,
                    role=None,
                    superuser=False,
                )

            actions.append(
                f"Entrée de menu '{entry_id}' créée sous Annuaire avec l'ordre {order}."
            )

        return actions

    def _repair_admin_user(self, dry_run=False):
        actions = []
        User = get_user_model()

        admin_user = User.objects.filter(username="admin").first()
        root_user = User.objects.filter(username="root").first()

        admin_created = False
        if admin_user is None:
            admin_user = User(username="admin")
            admin_created = True

        fields_to_update = []

        if admin_user.first_name != "Admin":
            admin_user.first_name = "Admin"
            fields_to_update.append("first_name")

        if admin_user.last_name != "ADMIN":
            admin_user.last_name = "ADMIN"
            fields_to_update.append("last_name")

        if admin_user.displayed_name != "Admin":
            admin_user.displayed_name = "Admin"
            fields_to_update.append("displayed_name")

        if admin_user.is_active is not True:
            admin_user.is_active = True
            fields_to_update.append("is_active")

        if admin_user.is_staff is not True:
            admin_user.is_staff = True
            fields_to_update.append("is_staff")

        if admin_user.is_superuser is not True:
            admin_user.is_superuser = True
            fields_to_update.append("is_superuser")

        password_updated = False
        if not admin_created and not admin_user.check_password("admin"):
            admin_user.set_password("admin")
            password_updated = True
        elif admin_created:
            admin_user.set_password("admin")
            password_updated = True

        if (admin_created or fields_to_update or password_updated) and not dry_run:
            admin_user.save()

        if admin_created:
            details = ["username", *fields_to_update]
            if password_updated:
                details.append("password")
            actions.append(
                "Utilisateur 'admin' créé et mis à jour : "
                + ", ".join(details)
                + "."
            )
        elif fields_to_update or password_updated:
            details = [*fields_to_update]
            if password_updated:
                details.append("password")
            actions.append(
                "Utilisateur 'admin' mis à jour : "
                + ", ".join(details)
                + "."
            )
        else:
            actions.append("Utilisateur 'admin' déjà conforme.")

        if root_user is not None:
            root_fields_to_update = []

            if root_user.is_active is not False:
                root_user.is_active = False
                root_fields_to_update.append("is_active")

            if root_fields_to_update and not dry_run:
                root_user.save(update_fields=root_fields_to_update)

            if root_fields_to_update:
                actions.append(
                    "Utilisateur 'root' mis à jour : "
                    + ", ".join(root_fields_to_update)
                    + "."
                )
            else:
                actions.append("Utilisateur 'root' déjà inactif.")
        else:
            actions.append("Utilisateur 'root' absent : aucune désactivation nécessaire.")

        return actions

    def _detach_fulbert(self, dry_run=False):
        actions = []
        User = get_user_model()

        try:
            admin_user = User.objects.get(username="admin")
        except User.DoesNotExist:
            actions.append("Utilisateur 'admin' introuvable : détachement de Fulbert ignoré.")
            return actions

        qs = Contact.objects.filter(
            first_name="Fulbert",
            last_name="CREME",
            is_user=admin_user,
        ).order_by("id")

        contacts = list(qs)

        if not contacts:
            actions.append("Aucun lien parasite Fulbert CREME -> admin à corriger.")
            return actions

        for contact in contacts:
            contact.is_user = None
            if not dry_run:
                contact.save(update_fields=["is_user"])

        ids = ", ".join(str(contact.id) for contact in contacts)
        actions.append(
            f"Lien parasite supprimé pour Fulbert CREME (contact(s) id : {ids})."
        )

        return actions
