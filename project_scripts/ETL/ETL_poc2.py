from pathlib import Path

import json
import pandas as pd


def first_valid_value(series):
    values = series.dropna()

    if values.empty:
        return pd.NA

    return values.iloc[0]


def build_full_name(first_name, last_name):
    values = []

    for value in [first_name, last_name]:
        if pd.notna(value):
            values.append(str(value).strip())

    if not values:
        return pd.NA

    return " ".join(values)


def split_people_list(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    text = text.replace(";", ",")
    text = text.replace("\n", ",")
    text = text.replace(" / ", ",")

    return [
        name.strip()
        for name in text.split(",")
        if name.strip()
    ]


def main():
    project_root = Path(__file__).resolve().parents[2]

    raw_file_path = (
        project_root
        / "project_data"
        / "raw"
        / "Entreprises entites stagiaires.csv"
    )

    processed_dir = project_root / "project_data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(
        raw_file_path,
        sep=";",
        encoding="cp1252",
        encoding_errors="replace",
        skiprows=21,
    )

    assert df_raw.shape[0] > 0
    assert df_raw.shape[1] == 24

    expected_columns = [
        "Unnamed: 0",
        "Code.Entité",
        "Libellé.Entité",
        "Code.Type d'entité",
        "Assujetti.Entité",
        "Rue (ligne 1).Adresse",
        "Rue (ligne 2).Adresse",
        "Rue (ligne 3).Adresse",
        "Rue (ligne 4).Adresse",
        "Code postal.Ville",
        "Nom.Ville",
        "Code.Type d'adresse",
        "Nombre de stage (sans contrat pro)",
        "Noms des stagiaires",
        "Nombre de contrat pro",
        "Noms des alternants contrats pro",
        "Nombre apprentissage",
        "Noms des apprentis",
        "Code.Type d'événement",
        "Montant global.Taxe versement",
        "Début.Événement",
        "Code.Fonctions",
        "Nom.Individu",
        "Prénom.Individu",
    ]

    missing_columns = set(expected_columns) - set(df_raw.columns)
    unexpected_columns = set(df_raw.columns) - set(expected_columns)

    assert not missing_columns, f"Colonnes manquantes : {missing_columns}"
    assert not unexpected_columns, f"Colonnes inattendues : {unexpected_columns}"

    df_work = df_raw.copy()

    columns_for_duplicates = df_work.columns.difference(["Unnamed: 0"])
    df_work = (
        df_work
        .drop_duplicates(subset=columns_for_duplicates, keep="first")
        .copy()
    )

    df_work = df_work.drop(columns=["Unnamed: 0"], errors="ignore")

    column_mapping = {
        "Code.Entité": "code_entite",
        "Libellé.Entité": "libelle_entite",
        "Code.Type d'entité": "type_entite",
        "Assujetti.Entité": "assujetti_entite",
        "Rue (ligne 1).Adresse": "adresse_ligne_1",
        "Rue (ligne 2).Adresse": "adresse_ligne_2",
        "Rue (ligne 3).Adresse": "adresse_ligne_3",
        "Rue (ligne 4).Adresse": "adresse_ligne_4",
        "Code postal.Ville": "code_postal",
        "Nom.Ville": "ville",
        "Code.Type d'adresse": "type_adresse",
        "Nombre de stage (sans contrat pro)": "nombre_stages",
        "Noms des stagiaires": "noms_stagiaires",
        "Nombre de contrat pro": "nombre_contrats_pro",
        "Noms des alternants contrats pro": "noms_alternants_contrats_pro",
        "Nombre apprentissage": "nombre_apprentissages",
        "Noms des apprentis": "noms_apprentis",
        "Code.Type d'événement": "type_evenement",
        "Montant global.Taxe versement": "montant_taxe",
        "Début.Événement": "debut_evenement",
        "Code.Fonctions": "fonction_contact",
        "Nom.Individu": "nom_contact",
        "Prénom.Individu": "prenom_contact",
    }

    df_work = df_work.rename(columns=column_mapping)

    text_columns = df_work.select_dtypes(include=["object", "string"]).columns

    for column in text_columns:
        df_work[column] = df_work[column].astype("string").str.strip()
        df_work[column] = df_work[column].replace("", pd.NA)

    count_columns = [
        "nombre_stages",
        "nombre_contrats_pro",
        "nombre_apprentissages",
    ]

    for column in count_columns:
        df_work[column] = pd.to_numeric(df_work[column], errors="coerce")

        non_missing_values = df_work[column].dropna()
        assert (non_missing_values % 1 == 0).all(), (
            f"Valeurs non entières détectées dans {column}"
        )

        df_work[column] = df_work[column].astype("Int64")

    date_with_time = pd.to_datetime(
        df_work["debut_evenement"],
        format="%d/%m/%Y %H:%M",
        errors="coerce",
    )

    date_without_time = pd.to_datetime(
        df_work["debut_evenement"],
        format="%d/%m/%Y",
        errors="coerce",
    )

    df_work["date_evenement"] = date_with_time.fillna(date_without_time)
    df_work["annee_evenement"] = df_work["date_evenement"].dt.year.astype("Int64")

    rows_with_event_date = df_work["debut_evenement"].notna()
    invalid_dates_count = (
        rows_with_event_date
        & df_work["date_evenement"].isna()
    ).sum()

    assert invalid_dates_count == 0

    montant_taxe_clean = (
        df_work["montant_taxe"]
        .astype("string")
        .str.replace(",", ".", regex=False)
        .str.replace(r"\s+", "", regex=True)
    )

    df_work["montant_taxe_decimal"] = pd.to_numeric(
        montant_taxe_clean,
        errors="coerce",
    )

    rows_with_montant = df_work["montant_taxe"].notna()
    invalid_montants_count = (
        rows_with_montant
        & df_work["montant_taxe_decimal"].isna()
    ).sum()

    assert invalid_montants_count == 0

    known_assujetti_values = df_work["assujetti_entite"].dropna().unique().tolist()

    assert set(known_assujetti_values) == {"Vrai"}, (
        f"Valeurs inattendues dans assujetti_entite : {known_assujetti_values}"
    )

    df_work["assujetti_entite_bool"] = (
        df_work["assujetti_entite"]
        .map({"Vrai": True})
        .astype("boolean")
    )

    df_entites = (
        df_work
        .groupby("code_entite", as_index=False)
        .agg({
            "libelle_entite": first_valid_value,
            "type_entite": first_valid_value,
            "assujetti_entite_bool": first_valid_value,
        })
    )

    contact_rows = df_work[
        df_work[["nom_contact", "prenom_contact"]]
        .notna()
        .any(axis=1)
    ].copy()

    df_contacts_pro = (
        contact_rows[
            [
                "code_entite",
                "libelle_entite",
                "nom_contact",
                "prenom_contact",
                "fonction_contact",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by=["code_entite", "nom_contact", "prenom_contact", "fonction_contact"],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    df_contacts_pro.insert(
        0,
        "contact_pro_id",
        [
            "contact_pro_" + str(index + 1).zfill(6)
            for index in range(len(df_contacts_pro))
        ],
    )

    address_columns = [
        "code_entite",
        "libelle_entite",
        "type_adresse",
        "adresse_ligne_1",
        "adresse_ligne_2",
        "adresse_ligne_3",
        "adresse_ligne_4",
        "code_postal",
        "ville",
    ]

    address_info_columns = [
        "type_adresse",
        "adresse_ligne_1",
        "adresse_ligne_2",
        "adresse_ligne_3",
        "adresse_ligne_4",
        "code_postal",
        "ville",
    ]

    address_rows = df_work[
        df_work[address_info_columns]
        .notna()
        .any(axis=1)
    ].copy()

    df_adresses = (
        address_rows[address_columns]
        .drop_duplicates()
        .sort_values(
            by=[
                "code_entite",
                "type_adresse",
                "adresse_ligne_1",
                "code_postal",
                "ville",
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    df_adresses.insert(
        0,
        "adresse_id",
        [
            "adresse_" + str(index + 1).zfill(6)
            for index in range(len(df_adresses))
        ],
    )

    taxe_rows = df_work[
        df_work["type_evenement"].eq("TAXE_VERSEMENT_ENTREPRISE")
    ].copy()

    taxe_key_columns = [
        "code_entite",
        "date_evenement",
        "montant_taxe_decimal",
    ]

    df_taxe_events = (
        taxe_rows
        .groupby(taxe_key_columns, as_index=False)
        .agg({
            "libelle_entite": first_valid_value,
            "type_evenement": first_valid_value,
            "montant_taxe": first_valid_value,
            "annee_evenement": first_valid_value,
        })
        .sort_values(
            by=["code_entite", "date_evenement", "montant_taxe_decimal"]
        )
        .reset_index(drop=True)
    )

    df_taxe_events.insert(
        0,
        "taxe_event_id",
        [
            "taxe_" + str(index + 1).zfill(6)
            for index in range(len(df_taxe_events))
        ],
    )

    suivi_columns = [
        "code_entite",
        "libelle_entite",
        "nombre_stages",
        "noms_stagiaires",
        "nombre_contrats_pro",
        "noms_alternants_contrats_pro",
        "nombre_apprentissages",
        "noms_apprentis",
    ]

    suivi_info_columns = [
        "nombre_stages",
        "noms_stagiaires",
        "nombre_contrats_pro",
        "noms_alternants_contrats_pro",
        "nombre_apprentissages",
        "noms_apprentis",
    ]

    suivi_rows = df_work[
        df_work[suivi_info_columns]
        .notna()
        .any(axis=1)
    ].copy()

    df_suivi_pedagogique = (
        suivi_rows[suivi_columns]
        .drop_duplicates()
        .sort_values(by=["code_entite", "libelle_entite"])
        .reset_index(drop=True)
    )

    df_suivi_pedagogique.insert(
        0,
        "suivi_id",
        [
            "suivi_" + str(index + 1).zfill(6)
            for index in range(len(df_suivi_pedagogique))
        ],
    )

    contact_crm_columns = [
        "code_entite",
        "libelle_entite",
        "nom_contact",
        "prenom_contact",
        "fonction_contact",
        "nom_complet_contact",
        "role_contact",
        "source_contact",
        "source_champ",
    ]

    df_contacts_pro_for_crm = df_contacts_pro[
        [
            "code_entite",
            "libelle_entite",
            "nom_contact",
            "prenom_contact",
            "fonction_contact",
        ]
    ].copy()

    df_contacts_pro_for_crm["nom_complet_contact"] = [
        build_full_name(row["prenom_contact"], row["nom_contact"])
        for _, row in df_contacts_pro_for_crm.iterrows()
    ]

    df_contacts_pro_for_crm["role_contact"] = (
        df_contacts_pro_for_crm["fonction_contact"]
        .fillna("CONTACT_ENTREPRISE")
    )

    df_contacts_pro_for_crm["source_contact"] = "CONTACT_PROFESSIONNEL"
    df_contacts_pro_for_crm["source_champ"] = "nom_contact / prenom_contact"

    pedagogical_sources = [
        ("noms_stagiaires", "STAGIAIRE"),
        ("noms_alternants_contrats_pro", "ALTERNANT_CONTRAT_PRO"),
        ("noms_apprentis", "APPRENTI"),
    ]

    pedagogical_rows = []

    for source_column, role_contact in pedagogical_sources:
        source_rows = (
            df_suivi_pedagogique[df_suivi_pedagogique[source_column].notna()]
            [["code_entite", "libelle_entite", source_column]]
            .drop_duplicates()
        )

        for _, row in source_rows.iterrows():
            for full_name in split_people_list(row[source_column]):
                pedagogical_rows.append({
                    "code_entite": row["code_entite"],
                    "libelle_entite": row["libelle_entite"],
                    "nom_contact": pd.NA,
                    "prenom_contact": pd.NA,
                    "fonction_contact": pd.NA,
                    "nom_complet_contact": full_name,
                    "role_contact": role_contact,
                    "source_contact": "SUIVI_PEDAGOGIQUE",
                    "source_champ": source_column,
                })

    df_contacts_pedagogiques = pd.DataFrame(
        pedagogical_rows,
        columns=contact_crm_columns,
    )

    df_contacts_pedagogiques = (
        df_contacts_pedagogiques
        .drop_duplicates(
            subset=[
                "code_entite",
                "nom_complet_contact",
                "role_contact",
            ]
        )
        .sort_values(
            by=["code_entite", "role_contact", "nom_complet_contact"]
        )
        .reset_index(drop=True)
    )

    df_contacts_pedagogiques.insert(
        0,
        "contact_pedagogique_id",
        [
            "contact_pedagogique_" + str(index + 1).zfill(6)
            for index in range(len(df_contacts_pedagogiques))
        ],
    )

    df_contacts_crm = (
        pd.concat(
            [
                df_contacts_pro_for_crm[contact_crm_columns],
                df_contacts_pedagogiques[contact_crm_columns],
            ],
            ignore_index=True,
        )
        .drop_duplicates(
            subset=[
                "code_entite",
                "nom_complet_contact",
                "role_contact",
            ]
        )
        .sort_values(
            by=["code_entite", "role_contact", "nom_complet_contact"]
        )
        .reset_index(drop=True)
    )

    df_contacts_crm.insert(
        0,
        "contact_crm_id",
        [
            "contact_crm_" + str(index + 1).zfill(6)
            for index in range(len(df_contacts_crm))
        ],
    )

    codes_entites = set(df_entites["code_entite"])

    tables_a_controler = {
        "contacts professionnels": df_contacts_pro,
        "contacts pédagogiques": df_contacts_pedagogiques,
        "contacts CRM qualifiés": df_contacts_crm,
        "adresses": df_adresses,
        "événements taxe": df_taxe_events,
        "suivi pédagogique": df_suivi_pedagogique,
    }

    for table_name, dataframe in tables_a_controler.items():
        assert dataframe["code_entite"].notna().all(), (
            f"{table_name} contient des lignes sans code_entite"
        )

        codes_invalides = set(dataframe["code_entite"]) - codes_entites

        assert not codes_invalides, (
            f"{table_name} rattachés à des entités inconnues : {codes_invalides}"
        )

    expected_sources = {"CONTACT_PROFESSIONNEL", "SUIVI_PEDAGOGIQUE"}
    actual_sources = set(df_contacts_crm["source_contact"].dropna().unique())

    assert actual_sources <= expected_sources, (
        f"Sources de contacts inattendues : {actual_sources - expected_sources}"
    )

    json_exports = {
        "poc2_entites.json": df_entites,
        "poc2_contacts_crm.json": df_contacts_crm,
        "poc2_adresses.json": df_adresses,
        "poc2_taxe_events.json": df_taxe_events,
        "poc2_suivi_pedagogique.json": df_suivi_pedagogique,
    }

    for file_name, dataframe in json_exports.items():
        output_path = processed_dir / file_name

        dataframe.to_json(
            output_path,
            orient="records",
            force_ascii=False,
            indent=2,
            date_format="iso",
        )

        assert output_path.exists(), f"Fichier non créé : {output_path}"

    expected_counts = {
        "poc2_entites.json": len(df_entites),
        "poc2_contacts_crm.json": len(df_contacts_crm),
        "poc2_adresses.json": len(df_adresses),
        "poc2_taxe_events.json": len(df_taxe_events),
        "poc2_suivi_pedagogique.json": len(df_suivi_pedagogique),
    }

    for file_name, expected_count in expected_counts.items():
        file_path = processed_dir / file_name

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        assert isinstance(data, list), (
            f"Le fichier {file_name} ne contient pas une liste JSON"
        )

        assert len(data) == expected_count, (
            f"Nombre d'objets incorrect dans {file_name} : "
            f"{len(data)} au lieu de {expected_count}"
        )

    etl_summary = {
        "lignes_source_brutes": len(df_raw),
        "lignes_apres_nettoyage": len(df_work),
        "entites": len(df_entites),
        "contacts_professionnels": len(df_contacts_pro),
        "contacts_pedagogiques": len(df_contacts_pedagogiques),
        "contacts_crm_qualifies": len(df_contacts_crm),
        "adresses": len(df_adresses),
        "evenements_taxe": len(df_taxe_events),
        "suivi_pedagogique": len(df_suivi_pedagogique),
    }

    assert etl_summary["lignes_source_brutes"] == 13345
    assert etl_summary["lignes_apres_nettoyage"] == 12435
    assert etl_summary["entites"] == 6738
    assert etl_summary["contacts_professionnels"] == 3982
    assert etl_summary["contacts_pedagogiques"] == 2192
    assert etl_summary["contacts_crm_qualifies"] == 6174

    print("ETL POC2 OK")
    print(f"Fichier source : {raw_file_path}")
    print(f"Dossier de sortie : {processed_dir}")

    for label, count in etl_summary.items():
        print(f"{label} : {count}")


if __name__ == "__main__":
    main()