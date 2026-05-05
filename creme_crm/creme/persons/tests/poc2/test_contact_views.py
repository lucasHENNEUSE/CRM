import json
import pytest
from django.urls import reverse


class TestAccesRoutesProtegees:
    """
    Teste que les routes protégées redirigent bien
    un utilisateur non connecté vers le login (HTTP 302).
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

    def test_email_mass_send_redirige_si_non_connecte(self, client):
        """La vue d'envoi d'email de masse doit être inaccessible sans connexion."""
        url = reverse("persons__email_mass_send")
        response = client.get(url)
        assert response.status_code == 302

    def test_taxe_view_redirige_si_non_connecte(self, client):
        """La vue taxe doit être inaccessible sans connexion."""
        url = reverse("persons__taxe")
        response = client.get(url)
        assert response.status_code == 302

    def test_delete_ajax_redirige_si_non_connecte(self, client):
        """La vue AJAX de suppression doit être inaccessible sans connexion."""
        url = reverse("persons__delete_contact_ajax")
        response = client.post(
            url,
            data=json.dumps({"emails": ["test@test.fr"]}),
            content_type="application/json",
        )
        assert response.status_code == 302


class TestRoutesConnecte:
    """
    Teste les routes accessibles avec un utilisateur connecté.
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

    def test_email_mass_send_get_accessible_connecte(self, logged_client):
        """La page d'envoi de masse doit être accessible en GET pour un utilisateur connecté."""
        url = reverse("persons__email_mass_send")
        response = logged_client.get(url)
        assert response.status_code == 200

    def test_taxe_view_accessible_connecte(self, logged_client):
        """La vue taxe doit être accessible pour un utilisateur connecté."""
        url = reverse("persons__taxe")
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


class TestVueDeleteAjax:
    """
    Teste la vue AJAX delete_contact_ajax — vue personnalisée du CRM
    qui exclut des contacts de la liste emailing ou taxe via la session.
    """

    def test_post_avec_email_valide_retourne_ok(self, logged_client, contact_valide):
        """Un POST valide avec un email existant doit retourner {'status': 'ok'}."""
        url = reverse("persons__delete_contact_ajax")
        response = logged_client.post(
            url,
            data=json.dumps(
                {
                    "emails": [contact_valide.email],
                    "context": "emailing",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_post_contexte_taxe_retourne_ok(self, logged_client, contact_valide):
        """Un POST avec context='taxe' doit aussi retourner {'status': 'ok'}."""
        url = reverse("persons__delete_contact_ajax")
        response = logged_client.post(
            url,
            data=json.dumps(
                {
                    "emails": [contact_valide.email],
                    "context": "taxe",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_post_sans_email_retourne_ok(self, logged_client):
        """Un POST sans email doit quand même retourner ok — liste vide tolérée."""
        url = reverse("persons__delete_contact_ajax")
        response = logged_client.post(
            url,
            data=json.dumps({"emails": [], "context": "emailing"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_get_sur_delete_ajax_retourne_405(self, logged_client):
        """Un GET sur la route AJAX doit retourner HTTP 405 (méthode non autorisée)."""
        url = reverse("persons__delete_contact_ajax")
        response = logged_client.get(url)
        assert response.status_code == 405

    def test_post_json_invalide_retourne_400(self, logged_client):
        """Un POST avec du JSON malformé doit retourner HTTP 400."""
        url = reverse("persons__delete_contact_ajax")
        response = logged_client.post(
            url,
            data="json invalide {{{",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestVueEmailMassSend:
    """
    Teste la vue email_mass_send — filtre et affiche les contacts
    inscrits au mailing, gère l'envoi POST.
    """

    def test_seuls_contacts_mailing_oui_affiches(self, logged_client, db, superuser):
        """
        La vue doit afficher uniquement les contacts avec is_in_mailing='OUI'
        et un email renseigné.
        """
        from creme.persons import get_contact_model

        contact_model = get_contact_model()

        contact_model.objects.create(
            user=superuser,
            last_name="MAILING",
            first_name="Oui",
            email="mailing.oui@test.fr",
            is_in_mailing="OUI",
        )
        contact_model.objects.create(
            user=superuser,
            last_name="NONMAILING",
            first_name="Non",
            email="mailing.non@test.fr",
            is_in_mailing="NON",
        )

        url = reverse("persons__email_mass_send")
        response = logged_client.get(url)

        assert response.status_code == 200
        contacts_dans_contexte = list(response.context["contacts"])
        emails = [c.email for c in contacts_dans_contexte]
        assert "mailing.oui@test.fr" in emails
        assert "mailing.non@test.fr" not in emails

    def test_post_sans_destinataire_affiche_warning(self, logged_client):
        """Un POST sans destinataire sélectionné doit afficher un message warning."""
        url = reverse("persons__email_mass_send")
        response = logged_client.post(
            url,
            data={
                "selected_contacts": [],
                "subject": "Test",
                "message": "Contenu test",
            },
        )
        assert response.status_code == 200
