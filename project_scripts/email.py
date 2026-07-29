import json
import os
import re
import datetime
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from openai import OpenAI

# 1. Configuration pour interroger OLLAMA SUR WSL
client_ai = OpenAI(
    base_url='http://127.0.0.1:11434/v1',
    api_key='ollama'
)

# 2. Configuration de l'API Brevo (Remplace par ta propre clé API Brevo)
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME")

# 3. Connexion à la base de données MongoDB locale (port 27018)
client_db = MongoClient('mongodb://localhost:27018/')
db = client_db['poc_aggregation']
collection_drafts = db['CampaignDraft']
collection_contacts = db['prospects_bruts']  

@csrf_exempt
def get_contacts(request):
    if request.method == 'GET':
        try:
            role_query = request.GET.get('role', '')
            search_query = request.GET.get('search', '').strip()
            
            query = {"is_in_emailing": "OUI"}
            
            if search_query:
                regex_pattern = {"$regex": search_query, "$options": "i"}
                query["$or"] = [
                    {"coordonnees.email": regex_pattern},
                    {"coordonnees.raw": regex_pattern},
                    {"contact.nom": regex_pattern},
                    {"contact.prenom": regex_pattern},
                    {"entite.libelle": regex_pattern},
                    {"entite.code": regex_pattern}
                ]
            
            contacts_cursor = collection_contacts.find(query).limit(100)
            
            contacts_list = []
            for doc in contacts_cursor:
                coordonnees = doc.get("coordonnees") or {}
                email = coordonnees.get("email") or coordonnees.get("raw") or ""
                
                if email:
                    contact = doc.get("contact") or {}
                    first_name = str(contact.get("prenom", "")).strip()
                    last_name = str(contact.get("nom", "")).strip() or "Prospect"
                    entite = doc.get("entite") or {}
                    company = str(entite.get("libelle") or entite.get("code") or "Organisation").strip()
                    
                    contacts_list.append({
                        "id": str(doc.get("_id")),
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "company": company,
                        "role": "prospect"
                    })
            
            if len(contacts_list) == 0:
                fallback_query = {}
                if search_query:
                    regex_pattern = {"$regex": search_query, "$options": "i"}
                    fallback_query["$or"] = [
                        {"coordonnees.email": regex_pattern},
                        {"coordonnees.raw": regex_pattern},
                        {"contact.nom": regex_pattern},
                        {"contact.prenom": regex_pattern},
                        {"entite.libelle": regex_pattern},
                        {"entite.code": regex_pattern}
                    ]
                
                for doc in collection_contacts.find(fallback_query).limit(50):
                    coordonnees = doc.get("coordonnees") or {}
                    email = coordonnees.get("email") or coordonnees.get("raw") or ""
                    if email:
                        contact = doc.get("contact") or {}
                        entite = doc.get("entite") or {}
                        contacts_list.append({
                            "id": str(doc.get("_id")),
                            "first_name": str(contact.get("prenom", "")).strip(),
                            "last_name": str(contact.get("nom", "")).strip() or "Prospect",
                            "email": str(email),
                            "company": str(entite.get("libelle", "Organisation")).strip(),
                            "role": "prospect"
                        })

            return JsonResponse({'status': 'success', 'contacts': contacts_list})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def generate_ai_email(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            target_role = data.get('target_role')
            template_type = data.get('template_type', 'invitation')
            image_url = data.get('image_url')
            attachments = data.get('attachments', [])
            instructions = data.get('instructions')
            tone = data.get('tone')
            language_level = data.get('language_level')

            system_prompt = f"""Tu es l'assistant IA de rédaction expert représentant l'ISEN (20 Rue Cuirassé Bretagne, 29200 Brest).
Ta mission est de rédiger un e-mail professionnel, direct, poli et extrêmement efficace. Fais attention à ce que tu dis.

PARAMÈTRES DE RÉDACTION :
- Public ciblé : {target_role}
- Ton souhaité : {tone}
- Niveau de langue : {language_level}

RÈGLES IMPÉRATIVES :
1. N'invente aucune date ni aucun lieu non spécifié dans le brief.
2. Signe obligatoirement par "L'équipe ISEN".
3. Ne mets aucun symbole de type émoticône ou emoji dans le texte généré.

Tu dois structurer ta réponse exactement avec ces balises textuelles :
[SUJET]: Objet persuasif et incitatif de l'email
[TITRE]: Grand titre principal sous la bannière
[CORPS]: Texte complet du message clair et professionnel
[BOUTON]: Texte court pour le bouton d'action"""

            response = client_ai.chat.completions.create(
                model="gemma:2b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Voici ma demande de rédaction : {instructions}"}
                ],
                temperature=0.3,
                max_tokens=350
            )

            raw_content = response.choices[0].message.content
            
            sub_match = re.search(r'\[SUJET\]:\s*(.*?)(?=\[TITRE\]|$)', raw_content, re.DOTALL)
            head_match = re.search(r'\[TITRE\]:\s*(.*?)(?=\[CORPS\]|$)', raw_content, re.DOTALL)
            body_match = re.search(r'\[CORPS\]:\s*(.*?)(?=\[BOUTON\]|$)', raw_content, re.DOTALL)
            btn_match = re.search(r'\[BOUTON\]:\s*(.*?)$', raw_content, re.DOTALL)

            subject = sub_match.group(1).strip() if sub_match else "Invitation - ISEN"
            headline = head_match.group(1).strip() if head_match else "Réunion stratégique"
            body = body_match.group(1).strip() if body_match else raw_content
            cta_button = btn_match.group(1).strip() if btn_match else "Confirmer ma présence"
            
            ai_result_json = {
                "subject": subject,
                "headline": headline,
                "body": body,
                "cta_button": cta_button
            }

            banner_html = ""
            if image_url and image_url.strip() != "":
                banner_html = f"""
                <div style="text-align: center;">
                    <img src="{image_url}" alt="Bannière de la campagne" style="width: 100%; max-height: 250px; object-fit: cover; display: block;">
                </div>
                """

            image_path = "http://127.0.0.1:8000/static_media/persons/isen.png"
            signature_isen_image = f"""
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e0e0e0; padding-top: 15px;">
                <img src="{image_path}" alt="ISEN" style="max-width: 120px; height: auto; display: block; margin: 0 auto;">
                <p style="font-size: 11px; color: #6c757d; margin-top: 5px;">ISEN - 20 Rue Cuirassé Bretagne, 29200 Brest</p>
            </div>
            """

            if template_type == 'invitation':
                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; background-color: #ffffff;">
                    {banner_html}
                    <div style="padding: 30px;">
                        <h2 style="color: #007bff; margin-top: 0; font-size: 22px;">{headline}</h2>
                        <div style="color: #333333; line-height: 1.6; white-space: pre-line; font-size: 15px;">{body}</div>
                        <div style="text-align: center; margin-top: 30px; margin-bottom: 10px;">
                            <a href="https://isen-nantes.fr" style="background-color: #007bff; color: white; padding: 14px 28px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">{cta_button}</a>
                        </div>
                        {signature_isen_image}
                    </div>
                </div>
                """
            elif template_type == 'newsletter':
                newsletter_image_block = f"""
                <div style="text-align: center; margin: 20px 0;">
                    <img src="{image_url}" alt="Illustration" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: 4px;">
                </div>
                """ if image_url and image_url.strip() != "" else ""

                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ced4da; background-color: #f8f9fa; padding: 20px;">
                    <div style="background-color: #ffffff; padding: 20px; border-bottom: 3px solid #6f42c1; text-align: center;">
                        <h1 style="color: #6f42c1; margin: 0; font-size: 24px;">NEWSLETTER ISEN</h1>
                    </div>
                    <div style="background-color: #ffffff; padding: 30px; margin-top: 15px;">
                        <h2 style="color: #2c3e50; margin-top: 0; font-size: 20px; border-left: 4px solid #6f42c1; padding-left: 10px;">{headline}</h2>
                        {newsletter_image_block}
                        <div style="color: #495057; line-height: 1.6; white-space: pre-line; font-size: 14px;">{body}</div>
                        <div style="text-align: right; margin-top: 20px;">
                            <a href="https://isen-nantes.fr" style="color: #6f42c1; font-weight: bold; text-decoration: none;">{cta_button} &rarr;</a>
                        </div>
                        {signature_isen_image}
                    </div>
                </div>
                """
            elif template_type == 'communique':
                communique_image_block = f"""
                <div style="margin: 30px 0; text-align: center;">
                    <img src="{image_url}" alt="Document officiel" style="max-width: 80%; height: auto; border: 1px solid #cccccc; padding: 5px;">
                </div>
                """ if image_url and image_url.strip() != "" else ""

                html_email = f"""
                <div style="font-family: 'Times New Roman', Times, serif; max-width: 600px; margin: 0 auto; border: 1px solid #333333; background-color: #ffffff; padding: 40px;">
                    <div style="border-bottom: 1px solid #333333; padding-bottom: 15px; margin-bottom: 25px;">
                        <strong style="font-family: Arial, sans-serif; font-size: 16px; color: #333333;">COMMUNIQUÉ INSTITUTIONNEL - ISEN</strong>
                    </div>
                    <h2 style="color: #111111; font-size: 22px; margin-top: 0; font-weight: normal;">{headline}</h2>
                    <div style="color: #222222; line-height: 1.8; white-space: pre-line; font-size: 16px; margin: 25px 0;">{body}</div>
                    {communique_image_block}
                    {signature_isen_image}
                </div>
                """
            else:  # Modèle classique (neutre)
                classic_image_block = f"""
                <div style="margin: 20px 0; text-align: center;">
                    <img src="{image_url}" alt="Illustration" style="max-width: 100%; height: auto; border-radius: 4px;">
                </div>
                """ if image_url and image_url.strip() != "" else ""

                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; background-color: #ffffff; padding: 30px;">
                    <h2 style="color: #333333; margin-top: 0; font-size: 20px; font-weight: bold;">{headline}</h2>
                    {classic_image_block}
                    <div style="color: #444444; line-height: 1.6; white-space: pre-line; font-size: 14px; margin: 20px 0;">{body}</div>
                    <div style="margin: 25px 0;">
                        <a href="https://isen-nantes.fr" style="background-color: #495057; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; font-size: 14px;">{cta_button}</a>
                    </div>
                    {signature_isen_image}
                </div>
                """

            draft_document = {
                "created_at": datetime.datetime.utcnow(),
                "status": "draft",
                "template_type": template_type,
                "visual_assets": {"image_url": image_url},
                "attachments": attachments,
                "targeting": {"target_role": target_role},
                "brief": {
                    "instructions": instructions,
                    "tone": tone,
                    "language_level": language_level
                },
                "ai_generation": ai_result_json,
                "final_html_rendered": html_email
            }
            inserted_draft = collection_drafts.insert_one(draft_document)

            return JsonResponse({
                'status': 'success',
                'draft_id': str(inserted_draft.inserted_id),
                'subject': subject,
                'body': body,
                'html_preview': html_email,
                'attachments_count': len(attachments)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def send_campaign_brevo(request):
    """
    Route API dédiée pour envoyer l'e-mail via l'API Brevo en mode démo.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipients = data.get('recipients', []) # Liste d'emails sélectionnés
            subject = data.get('subject', 'Campagne ISEN')
            html_content = data.get('html_content', '')

            if not recipients:
                return JsonResponse({'status': 'error', 'error': "Aucun destinataire sélectionné."}, status=400)

            # Formatage des destinataires pour l'API Brevo
            to_list = [{"email": email} for email in recipients]

            brevo_payload = {
                "sender": {
                    "name": SENDER_NAME,
                    "email": SENDER_EMAIL
                },
                "to": to_list,
                "subject": subject,
                "htmlContent": html_content
            }

            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json"
            }

            response = requests.post("https://api.brevo.com/v3/smtp/email", json=brevo_payload, headers=headers)

            if response.status_code in [200, 201]:
                return JsonResponse({'status': 'success', 'message': "Campagne envoyée avec succès via Brevo !"})
            else:
                return JsonResponse({'status': 'error', 'error': f"Erreur Brevo : {response.text}"}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
