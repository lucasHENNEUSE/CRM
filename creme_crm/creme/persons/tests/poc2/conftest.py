import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


# Fixtures partagées entre tous les fichiers de test.
# Elles sont automatiquement disponibles sans import explicite.


@pytest.fixture(scope="session", autouse=True)
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("creme_populate")


@pytest.fixture
def superuser(db):
    """
    Crée un superutilisateur Django réutilisable dans tous les tests.
    Le paramètre 'db' donne accès à la base de données de test.
    """
    user_model = get_user_model()
    return user_model.objects.create_superuser(
        username="admin_test",
        password="test1234!",
        email="admin@test.fr",
        last_name="Admin",
        first_name="Test",
    )


@pytest.fixture
def logged_client(client, superuser):
    """
    Retourne un client Django déjà authentifié en tant que superutilisateur.
    Utilise la fixture 'superuser' définie ci-dessus.
    """
    client.force_login(superuser)
    return client


@pytest.fixture
def contact_valide(db, superuser):
    """
    Crée un contact valide minimal en base de données de test.
    Utilisé comme point de départ dans les tests qui ont besoin d'un contact existant.
    """
    from creme.persons import get_contact_model

    contact_model = get_contact_model()

    return contact_model.objects.create(
        user=superuser,
        last_name="DUPONT",
        first_name="Jean",
        email="jean.dupont@test.fr",
    )
