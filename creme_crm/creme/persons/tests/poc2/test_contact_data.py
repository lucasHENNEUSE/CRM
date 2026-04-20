import pytest
from creme.persons import get_contact_model


class TestIntegriteBase:
    """
    Teste les opérations CRUD de base et la cohérence
    des données stockées en base pour le modèle Contact.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_creation_contact_minimal(self, db, superuser):
        """Un contact avec seulement last_name doit pouvoir être créé."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="MINIMAL",
        )
        assert contact.id is not None
        assert contact.last_name == "MINIMAL"

    def test_contact_retrouvable_par_email(self, db, superuser):
        """Un contact créé doit être retrouvable par son email en base."""
        self.Contact.objects.create(
            user=superuser,
            last_name="RETROUVE",
            first_name="Test",
            email="retrouve@test.fr",
        )
        found = self.Contact.objects.filter(email="retrouve@test.fr").first()
        assert found is not None
        assert found.last_name == "RETROUVE"

    def test_contact_retrouvable_par_nom(self, db, superuser):
        """Un contact créé doit être retrouvable par son nom en base."""
        self.Contact.objects.create(
            user=superuser,
            last_name="RECHERCHE",
            first_name="Par",
            email="recherche@test.fr",
        )
        found = self.Contact.objects.filter(last_name="RECHERCHE").first()
        assert found is not None

    def test_mise_a_jour_email(self, db, contact_valide):
        """La mise à jour d'un email doit être persistée en base."""
        contact_valide.email = "nouveau@test.fr"
        contact_valide.save()

        refreshed = self.Contact.objects.get(id=contact_valide.id)
        assert refreshed.email == "nouveau@test.fr"

    def test_suppression_contact(self, db, contact_valide):
        """Un contact supprimé ne doit plus être retrouvable en base."""
        contact_id = contact_valide.id
        contact_valide.delete()
        assert self.Contact.objects.filter(id=contact_id).count() == 0

    def test_ordering_par_nom_prenom(self, db, superuser):
        """
        Les contacts doivent être triés par last_name puis first_name
        conformément au Meta.ordering du modèle.
        """
        self.Contact.objects.create(user=superuser, last_name="ZOLA", first_name="Emile", email="zola@test.fr")
        self.Contact.objects.create(user=superuser, last_name="AUBERT", first_name="Claire", email="aubert@test.fr")
        self.Contact.objects.create(user=superuser, last_name="MARTIN", first_name="Alice", email="martin@test.fr")

        contacts = list(
            self.Contact.objects.filter(last_name__in=["ZOLA", "AUBERT", "MARTIN"])
        )
        noms = [c.last_name for c in contacts]

        assert noms.index("AUBERT") < noms.index("MARTIN") < noms.index("ZOLA")


class TestFiltresMetier:
    """
    Teste les filtres métier utilisés dans les vues email_mass_send et taxe_view.
    Ces filtres sont critiques car ils déterminent qui reçoit les emails.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_filtre_mailing_oui_exclut_non(self, db, superuser):
        """
        Le filtre is_in_mailing='OUI' ne doit retourner
        que les contacts inscrits, pas les autres.
        """
        self.Contact.objects.create(
            user=superuser,
            last_name="OUI1",
            email="oui1@test.fr",
            is_in_mailing="OUI",
        )
        self.Contact.objects.create(
            user=superuser,
            last_name="NON1",
            email="non1@test.fr",
            is_in_mailing="NON",
        )

        inscrits = self.Contact.objects.filter(is_in_mailing="OUI", email__gt="")
        noms = [c.last_name for c in inscrits]

        assert "OUI1" in noms
        assert "NON1" not in noms

    def test_filtre_taxe_oui_exclut_non(self, db, superuser):
        """
        Le filtre is_in_taxe='OUI' ne doit retourner
        que les contacts assujettis à la taxe.
        """
        self.Contact.objects.create(
            user=superuser,
            last_name="TAXEOUI",
            email="taxeoui@test.fr",
            is_in_taxe="OUI",
        )
        self.Contact.objects.create(
            user=superuser,
            last_name="TAXENON",
            email="taxenon@test.fr",
            is_in_taxe="NON",
        )

        assujettis = self.Contact.objects.filter(is_in_taxe="OUI", email__gt="")
        noms = [c.last_name for c in assujettis]

        assert "TAXEOUI" in noms
        assert "TAXENON" not in noms

    def test_filtre_exclut_email_vide(self, db, superuser):
        """
        Les contacts sans email ne doivent jamais apparaître
        dans les listes mailing ou taxe.
        """
        self.Contact.objects.create(
            user=superuser,
            last_name="SANSEMAIL",
            email="",
            is_in_mailing="OUI",
        )

        contacts = self.Contact.objects.filter(is_in_mailing="OUI").exclude(email="")

        noms = [c.last_name for c in contacts]
        assert "SANSEMAIL" not in noms

    def test_exclusion_par_ids_session(self, db, superuser):
        """
        Simule l'exclusion de contacts via les IDs de session
        comme le fait la vue email_mass_send.
        """
        self.Contact.objects.create(
            user=superuser,
            last_name="INCLUS",
            email="inclus@test.fr",
            is_in_mailing="OUI",
        )
        c2 = self.Contact.objects.create(
            user=superuser,
            last_name="EXCLU",
            email="exclu@test.fr",
            is_in_mailing="OUI",
        )

        removed_ids = [c2.id]

        contacts = (
            self.Contact.objects.filter(is_in_mailing="OUI")
            .exclude(email="")
            .exclude(id__in=removed_ids)
        )

        noms = [c.last_name for c in contacts]
        assert "INCLUS" in noms
        assert "EXCLU" not in noms

    def test_champs_entite_stockes_correctement(self, db, superuser):
        """
        Vérifie que les champs métier spécifiques (entity_code, entity_label,
        is_entity_subject) sont bien stockés et récupérés.
        """
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="ENTITE",
            first_name="Test",
            email="entite@test.fr",
            entity_code="ENT001",
            entity_label="ISEN Brest",
            is_entity_subject=True,
            education_nb_stagiaires=25,
        )

        refreshed = self.Contact.objects.get(id=contact.id)
        assert refreshed.entity_code == "ENT001"
        assert refreshed.entity_label == "ISEN Brest"
        assert refreshed.is_entity_subject is True
        assert refreshed.education_nb_stagiaires == 25
        