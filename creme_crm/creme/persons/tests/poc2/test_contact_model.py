import pytest
from django.core.exceptions import ValidationError
from creme.persons import get_contact_model


class TestNormalisationContact:
    """
    Teste que la méthode save() normalise correctement les données
    avant de les écrire en base : majuscules, title case, lowercase email, strip.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_last_name_passe_en_majuscules(self, db, superuser):
        """Le nom doit être sauvegardé en MAJUSCULES peu importe la saisie."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="dupont",
            first_name="Jean",
            email="jean.dupont@test.fr",
        )
        assert contact.last_name == "DUPONT"

    def test_first_name_passe_en_title_case(self, db, superuser):
        """Le prénom doit avoir chaque mot avec une majuscule initiale."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="MARTIN",
            first_name="jean-paul",
            email="jp.martin@test.fr",
        )
        assert contact.first_name == "Jean-Paul"

    def test_email_passe_en_minuscules(self, db, superuser):
        """L'email doit toujours être stocké en minuscules."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="LEBLANC",
            first_name="Marie",
            email="Marie.LeBlanc@TEST.FR",
        )
        assert contact.email == "marie.leblanc@test.fr"

    def test_last_name_spaces_supprimes(self, db, superuser):
        """Les espaces en début et fin de nom doivent être supprimés."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="  BERNARD  ",
            first_name="Pierre",
            email="pierre.bernard@test.fr",
        )
        assert contact.last_name == "BERNARD"

    def test_email_spaces_supprimes(self, db, superuser):
        """Les espaces autour de l'email doivent être supprimés avant sauvegarde."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="PETIT",
            first_name="Lucie",
            email="  lucie.petit@test.fr  ",
        )
        assert contact.email == "lucie.petit@test.fr"

    def test_entity_code_spaces_supprimes(self, db, superuser):
        """Les espaces autour du code entité doivent être supprimés."""
        contact = self.Contact.objects.create(
            user=superuser,
            last_name="ROBERT",
            first_name="Alain",
            email="alain.robert@test.fr",
            entity_code="  ENT001  ",
        )
        assert contact.entity_code == "ENT001"


class TestValidationContact:
    """
    Teste la méthode clean() qui valide les données avant sauvegarde.
    Ces tests vérifient que les erreurs métier sont bien levées.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_email_invalide_sans_arobase_leve_erreur(self, db, superuser):
        """Un email sans @ doit lever une ValidationError."""
        contact = self.Contact(
            user=superuser,
            last_name="TEST",
            first_name="Erreur",
            email="emailsansarobase.fr",
        )
        with pytest.raises(ValidationError) as exc_info:
            contact.clean()
        assert "email" in exc_info.value.message_dict

    def test_email_avec_espace_leve_erreur(self, db, superuser):
        """Un email contenant un espace doit lever une ValidationError."""
        contact = self.Contact(
            user=superuser,
            last_name="TEST",
            first_name="Erreur",
            email="email avec espace@test.fr",
        )
        with pytest.raises(ValidationError) as exc_info:
            contact.clean()
        assert "email" in exc_info.value.message_dict

    def test_telephone_avec_lettres_leve_erreur(self, db, superuser):
        """Un numéro de téléphone avec des lettres doit lever une ValidationError."""
        contact = self.Contact(
            user=superuser,
            last_name="TEST",
            first_name="Erreur",
            email="test@test.fr",
            phone="06AB12CD34",
        )
        with pytest.raises(ValidationError) as exc_info:
            contact.clean()
        assert "phone" in exc_info.value.message_dict

    def test_telephone_valide_accepte(self, db, superuser):
        """Un numéro de téléphone avec chiffres, espaces et + doit être accepté."""
        contact = self.Contact(
            user=superuser,
            last_name="TEST",
            first_name="Valide",
            email="valide@test.fr",
            phone="+33 06 12 34 56 78",
        )
        contact.clean()

    def test_mobile_avec_tirets_accepte(self, db, superuser):
        """Un mobile avec des tirets doit être accepté."""
        contact = self.Contact(
            user=superuser,
            last_name="TEST",
            first_name="Valide",
            email="valide2@test.fr",
            mobile="06-12-34-56-78",
        )
        contact.clean()

    def test_contact_lie_utilisateur_sans_prenom_leve_erreur(self, db, superuser):
        """Un contact lié à un user sans prénom doit lever une ValidationError."""
        contact = self.Contact(
            user=superuser,
            last_name="ADMIN",
            first_name="",
            email="admin@test.fr",
            is_user=superuser,
        )
        with pytest.raises(ValidationError) as exc_info:
            contact.clean()
        assert "first_name" in exc_info.value.message_dict

    def test_contact_lie_utilisateur_sans_email_leve_erreur(self, db, superuser):
        """Un contact lié à un user sans email doit lever une ValidationError."""
        contact = self.Contact(
            user=superuser,
            last_name="ADMIN",
            first_name="Test",
            email="",
            is_user=superuser,
        )
        with pytest.raises(ValidationError) as exc_info:
            contact.clean()
        assert "email" in exc_info.value.message_dict


class TestDoublonContact:
    """
    Teste la détection des doublons dans clean().
    Un contact avec le même nom + prénom + email ne doit pas pouvoir être créé deux fois.
    """

    @pytest.fixture(autouse=True)
    def setup_model(self):
        self.Contact = get_contact_model()

    def test_doublon_exact_detecte(self, db, superuser, contact_valide):
        """
        Tenter de créer un contact identique (même nom, prénom, email)
        doit lever une ValidationError signalant le doublon.
        """
        doublon = self.Contact(
            user=superuser,
            last_name="DUPONT",
            first_name="Jean",
            email="jean.dupont@test.fr",
        )
        with pytest.raises(ValidationError):
            doublon.clean()

    def test_meme_nom_email_different_accepte(self, db, superuser, contact_valide):
        """
        Même nom et prénom mais email différent ne doit pas être considéré comme doublon.
        """
        contact_different = self.Contact(
            user=superuser,
            last_name="DUPONT",
            first_name="Jean",
            email="jean.dupont.pro@test.fr",
        )
        contact_different.clean()

    def test_modification_contact_existant_pas_doublon(self, db, superuser, contact_valide):
        """
        Modifier un contact existant (id non nul) ne doit pas déclencher
        la vérification de doublon — on ne vérifie qu'à la création.
        """
        contact_valide.first_name = "Jean-Pierre"
        contact_valide.clean()


class TestRepresentationContact:
    """
    Vérifie la représentation texte d'un contact.
    """

    def test_str_contact_avec_prenom_et_nom(self, db, superuser):
        """La représentation string d'un contact doit retourner prénom + nom."""
        contact = get_contact_model()(
            user=superuser,
            last_name="DUPONT",
            first_name="Jean",
            email="jean@test.fr",
        )
        assert "DUPONT" in str(contact)
        assert "Jean" in str(contact)
