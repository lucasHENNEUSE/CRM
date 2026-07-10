from django.urls import reverse


class TestAccesRoutesProtegees:
    """
    Vérifie que les routes principales Contacts redirigent
    un utilisateur non connecté vers le login.
    """

    def test_liste_contacts_redirige_si_non_connecte(self, client):
        """La liste des contacts doit être inaccessible sans connexion."""
        url = reverse("persons__list_contacts")
        response = client.get(url)
        assert response.status_code == 302

    def test_creation_contact_redirige_si_non_connecte(self, client):
        """La page de création de contact doit être inaccessible sans connexion."""
        url = reverse("persons__create_contact")
        response = client.get(url)
        assert response.status_code == 302


class TestRoutesConnecte:
    """
    Vérifie les routes principales Contacts utilisées par le POC2.
    """

    def test_liste_contacts_accessible_connecte(self, logged_client):
        """La liste des contacts doit être accessible pour un utilisateur connecté."""
        url = reverse("persons__list_contacts")
        response = logged_client.get(url)
        assert response.status_code == 200

    def test_creation_contact_accessible_connecte(self, logged_client):
        """La page de création doit être accessible pour un utilisateur connecté."""
        url = reverse("persons__create_contact")
        response = logged_client.get(url)
        assert response.status_code == 200

    def test_detail_contact_accessible(self, logged_client, contact_valide):
        """La page détail d'un contact existant doit retourner HTTP 200."""
        url = reverse("persons__view_contact", args=[contact_valide.id])
        response = logged_client.get(url)
        assert response.status_code == 200

    def test_detail_contact_inexistant_retourne_404(self, logged_client):
        """Accéder à un contact avec un ID inexistant doit retourner HTTP 404."""
        url = reverse("persons__view_contact", args=[999999])
        response = logged_client.get(url)
        assert response.status_code == 404

    def test_edition_contact_accessible(self, logged_client, contact_valide):
        """La page d'édition d'un contact existant doit être accessible."""
        url = reverse("persons__edit_contact", args=[contact_valide.id])
        response = logged_client.get(url)
        assert response.status_code == 200
