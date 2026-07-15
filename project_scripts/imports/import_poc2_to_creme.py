"""
Dry-run d'import POC2 vers CremeCRM.

Ce script simule le mapping des données POC2 vers CremeCRM sans écrire en base.

Objectif :
- vérifier les volumes ;
- vérifier les rattachements par code_entite ;
- préparer l'import réel Organisations / Contacts / Adresses / Relations.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ROOT = PROJECT_ROOT / "project_data" / "processed"

FILES = {
    "entites": "poc2_entites.json",
    "contacts": "poc2_contacts_crm.json",
    "adresses": "poc2_adresses.json",
    "taxe_events": "poc2_taxe_events.json",
    "suivi_pedagogique": "poc2_suivi_pedagogique.json",
}

ROLES_MANAGES = {"DIRECTION", "DIRECTION_RH"}
ROLES_EMPLOYED_BY = {"STAGIAIRE", "APPRENTI", "ALTERNANT_CONTRAT_PRO"}


def load_json(filename: str) -> list[dict]:
    path = PROCESSED_ROOT / filename
    return json.loads(path.read_text(encoding="utf-8"))


def has_address_line(row: dict) -> bool:
    return any(
        row.get(key)
        for key in (
            "adresse_ligne_1",
            "adresse_ligne_2",
            "adresse_ligne_3",
            "adresse_ligne_4",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prépare l'import POC2 vers CremeCRM en mode dry-run."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le dry-run aux N premières entités pour tester un échantillon.",
    )
    parser.add_argument(
        "--check-django",
        action="store_true",
        help="Vérifier l'accès à Django/CremeCRM sans écrire en base.",
    )
    return parser.parse_args()


def setup_django() -> None:
    creme_root = PROJECT_ROOT / "creme_crm"
    sys.path.insert(0, str(creme_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creme.dev_settings")

    import django
    django.setup()


def check_django_access() -> None:
    setup_django()

    from django.contrib.auth import get_user_model
    from creme.creme_core.models import RelationType
    from creme.persons.models import Address, Contact, Organisation
    from creme.persons import constants

    User = get_user_model()

    print("=== Vérification Django / CremeCRM ===")

    admin_user = User.objects.filter(username="admin").first()
    if admin_user is None:
        print("Utilisateur admin : introuvable")
    else:
        print(
            "Utilisateur admin : OK "
            f"(id={admin_user.id}, active={admin_user.is_active}, "
            f"staff={admin_user.is_staff}, superuser={admin_user.is_superuser})"
        )

    print(f"Modèle Organisation : OK ({Organisation._meta.label})")
    print(f"Modèle Contact      : OK ({Contact._meta.label})")
    print(f"Modèle Address      : OK ({Address._meta.label})")

    relation_ids = [
        constants.REL_SUB_MANAGES,
        constants.REL_SUB_EMPLOYED_BY,
    ]

    for relation_id in relation_ids:
        exists = RelationType.objects.filter(id=relation_id).exists()
        print(f"RelationType {relation_id} : {'OK' if exists else 'introuvable'}")


def main() -> None:
    args = parse_args()

    if args.check_django:
        check_django_access()
        print()

    entites = load_json(FILES["entites"])
    contacts = load_json(FILES["contacts"])
    adresses = load_json(FILES["adresses"])
    taxe_events = load_json(FILES["taxe_events"])
    suivi_pedagogique = load_json(FILES["suivi_pedagogique"])

    if args.limit is not None:
        selected_codes = {
            row["code_entite"]
            for row in entites[:args.limit]
            if row.get("code_entite")
        }

        entites = [
            row for row in entites
            if row.get("code_entite") in selected_codes
        ]
        contacts = [
            row for row in contacts
            if row.get("code_entite") in selected_codes
        ]
        adresses = [
            row for row in adresses
            if row.get("code_entite") in selected_codes
        ]
        taxe_events = [
            row for row in taxe_events
            if row.get("code_entite") in selected_codes
        ]
        suivi_pedagogique = [
            row for row in suivi_pedagogique
            if row.get("code_entite") in selected_codes
        ]

    entites_by_code = {
        row["code_entite"]: row
        for row in entites
        if row.get("code_entite")
    }

    print("=== DRY-RUN IMPORT POC2 VERS CREMECRM ===")
    print("Aucune écriture en base ne sera effectuée.")
    if args.limit is not None:
        print(f"Échantillon limité aux {args.limit} premières entités sources.")
    print()

    print("=== Volumes sources ===")
    print(f"Entités              : {len(entites)}")
    print(f"Contacts CRM         : {len(contacts)}")
    print(f"Adresses             : {len(adresses)}")
    print(f"Événements taxe      : {len(taxe_events)}")
    print(f"Suivis pédagogiques  : {len(suivi_pedagogique)}")
    print()

    entites_sans_code = [e for e in entites if not e.get("code_entite")]
    entites_sans_nom = [e for e in entites if not e.get("libelle_entite")]
    codes_entites_trop_longs = [
        e for e in entites
        if e.get("code_entite") and len(str(e["code_entite"])) > 30
    ]

    print("=== Organisations simulées ===")
    print(f"Organisations créables depuis entités : {len(entites_by_code)}")
    print(f"Entités sans code_entite              : {len(entites_sans_code)}")
    print(f"Entités sans libelle_entite           : {len(entites_sans_nom)}")
    print(f"Codes entité > 30 caractères          : {len(codes_entites_trop_longs)}")
    print("Règle : code_entite complet stocké dans extra_data, pas dans Organisation.code.")
    print("Règle : si libelle_entite est vide, Organisation.name prendra code_entite.")
    print()

    contacts_sans_entite = [
        c for c in contacts
        if c.get("code_entite") not in entites_by_code
    ]

    contacts_sans_nom_exploitable = [
        c for c in contacts
        if not (c.get("nom_contact") or c.get("nom_complet_contact"))
    ]

    roles = Counter(c.get("role_contact") for c in contacts)
    sources = Counter(c.get("source_contact") for c in contacts)

    relations_manages = 0
    relations_employed_by = 0
    relations_role_inconnu = 0

    for contact in contacts:
        role = contact.get("role_contact")

        if role in ROLES_MANAGES:
            relations_manages += 1
        elif role in ROLES_EMPLOYED_BY:
            relations_employed_by += 1
        else:
            relations_role_inconnu += 1

    print("=== Contacts simulés ===")
    print(f"Contacts créables depuis contacts_crm : {len(contacts)}")
    print(f"Contacts sans entité correspondante   : {len(contacts_sans_entite)}")
    print(f"Contacts sans nom exploitable         : {len(contacts_sans_nom_exploitable)}")
    print()

    print("Répartition des rôles :")
    for role, count in roles.most_common():
        print(f"  - {role}: {count}")
    print()

    print("Répartition des sources :")
    for source, count in sources.most_common():
        print(f"  - {source}: {count}")
    print()

    print("=== Relations Contact ↔ Organisation simulées ===")
    print(f"Relations responsables à créer        : {relations_manages}")
    print(f"Relations salariés/rattachés à créer  : {relations_employed_by}")
    print(f"Rôles non mappés en relation          : {relations_role_inconnu}")
    print()

    adresses_sans_entite = [
        a for a in adresses
        if a.get("code_entite") not in entites_by_code
    ]

    adresses_sans_ligne = [
        a for a in adresses
        if not has_address_line(a)
    ]

    types_adresses = Counter(a.get("type_adresse") for a in adresses)

    adresses_par_entite = defaultdict(list)
    for adresse in adresses:
        if adresse.get("code_entite") in entites_by_code:
            adresses_par_entite[adresse["code_entite"]].append(adresse)

    print("=== Adresses simulées ===")
    print(f"Adresses rattachables à une entité    : {len(adresses) - len(adresses_sans_entite)}")
    print(f"Adresses sans entité correspondante   : {len(adresses_sans_entite)}")
    print(f"Adresses sans ligne d'adresse         : {len(adresses_sans_ligne)}")
    print(f"Entités ayant au moins une adresse    : {len(adresses_par_entite)}")
    print()

    print("Répartition des types d'adresse :")
    for type_adresse, count in types_adresses.most_common():
        print(f"  - {type_adresse}: {count}")
    print()

    print("=== Données conservées hors import v1 ===")
    print(f"Événements taxe conservés dans Mongo  : {len(taxe_events)}")
    print(f"Suivis pédagogiques conservés dans Mongo : {len(suivi_pedagogique)}")
    print()

    print("=== Exemples à contrôler ===")

    if entites_sans_nom:
        print()
        print("Entités sans libellé, exemples :")
        for row in entites_sans_nom[:5]:
            print(f"  - {row}")

    if contacts_sans_entite:
        print()
        print("Contacts sans entité correspondante, exemples :")
        for row in contacts_sans_entite[:5]:
            print(f"  - {row}")

    if contacts_sans_nom_exploitable:
        print()
        print("Contacts sans nom exploitable, exemples :")
        for row in contacts_sans_nom_exploitable[:5]:
            print(f"  - {row}")

    if adresses_sans_entite:
        print()
        print("Adresses sans entité correspondante, exemples :")
        for row in adresses_sans_entite[:5]:
            print(f"  - {row}")

    print()
    print("=== Conclusion dry-run ===")
    print("Mapping POC2 simulé sans écriture en base.")


if __name__ == "__main__":
    main()
