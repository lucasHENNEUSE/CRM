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
        """Un contact créé doit être retrouvé par son email en base."""
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
        """Un contact créé doit être retrouvé par son nom en base."""
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
        """Un contact supprimé ne doit plus être retrouvé en base."""
        contact_id = contact_valide.id
        contact_valide.delete()
        assert self.Contact.objects.filter(id=contact_id).count() == 0

    def test_ordering_par_nom_prenom(self, db, superuser):
        """
        Les contacts doivent être triés par last_name puis first_name
        conformément au Meta.ordering du modèle.
        """
        self.Contact.objects.create(
            user=superuser,
            last_name="ZOLA",
            first_name="Emile",
            email="zola@test.fr",
        )
        self.Contact.objects.create(
            user=superuser,
            last_name="AUBERT",
            first_name="Claire",
            email="aubert@test.fr",
        )
        self.Contact.objects.create(
            user=superuser,
            last_name="MARTIN",
            first_name="Alice",
            email="martin@test.fr",
        )

        contacts = list(
            self.Contact.objects.filter(last_name__in=["ZOLA", "AUBERT", "MARTIN"])
        )
        noms = [c.last_name for c in contacts]

        assert noms.index("AUBERT") < noms.index("MARTIN") < noms.index("ZOLA")


class TestChampsContactPOC2:
    """
    Vérifie les champs utiles au POC2 qui restent dans le modèle Contact.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_champs_entite_stockes_correctement(self, db, superuser):
        """
        Vérifie que les champs liés à l'entité et au suivi pédagogique
        sont stockés et récupérés correctement.
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
