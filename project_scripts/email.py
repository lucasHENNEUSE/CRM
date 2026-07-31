import json
import re
import datetime
import base64
import logging
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

client_ai = OpenAI(
    base_url='http://127.0.0.1:11434/v1',
    api_key='ollama'
)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME")

client_db = MongoClient('mongodb://localhost:27018/')
db = client_db['poc_aggregation']
collection_drafts = db['CampaignDraft']
collection_contacts = db['prospects_bruts']  

def get_default_isen_image_base64():
    current_dir = os.path.dirname(__file__)
    possible_paths = [
        os.path.join(current_dir, '../creme_crm/static/persons/isen.png'),
        os.path.join(current_dir, 'creme_crm/static/persons/isen.png'),
        'creme_crm/static/persons/isen.png',
        'static/persons/isen.png',
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    return f"data:image/png;base64,{encoded_string}"
            except Exception as e:
                print(f"Erreur lecture isen.png: {e}")
    return ""


@csrf_exempt
def get_contacts(request):
    if request.method == 'GET':
        try:
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
            
            selected_recipients = data.get('recipients', [])
            template_type = data.get('template_type', 'invitation')
            image_url = data.get('image_url')
            
            attachments = data.get('attachments', [])
            instructions = data.get('instructions')
            tone = data.get('tone', 'professionnel_chaleureux')
            language_level = data.get('language_level', 'vouvoiement')

            salutation_prefix = "Bonjour,"
            if len(selected_recipients) == 1:
                single_email = selected_recipients[0]
                contact_doc = collection_contacts.find_one({
                    "$or": [{"coordonnees.email": single_email}, {"coordonnees.raw": single_email}]
                })
                if contact_doc:
                    c_info = contact_doc.get("contact", {})
                    f_name = c_info.get("prenom", "").strip()
                    l_name = c_info.get("nom", "").strip()
                    full_name_str = f"{f_name} {l_name}".strip()
                    if full_name_str:
                        salutation_prefix = f"Bonjour {full_name_str},"

            system_prompt = f"""Tu rédiges un e-mail professionnel pour l'école d'ingénieurs ISEN Ouest.
Rédige uniquement le corps de l'e-mail (3 à 4 paragraphes), poli et engageant.

PARAMÈTRES DE STYLE :
- Ton : {tone}
- Langue : {language_level}
- Commence directement le message par cette formule exacte : "{salutation_prefix}"

INTERDICTIONS ABSOLUES :
1. N'ajoute AUCUNE balise de type [SUJET], [TITRE], [CORPS] ou [BOUTON].
2. N'écris JAMAIS "L'équipe d'Isen Ouest" au milieu ou au début du texte.
3. N'ajoute AUCUNE signature en fin de texte (pas de "Cordialement", pas de "L'équipe d'Isen Ouest"). La signature finale est gérée automatiquement.
4. Aucun emoji.
5. Ne mentionne jamais que tu es un assistant ou une IA.
6. signe toujours à la fin des mails L'équipe d'Isen Ouest (mais pas au milieu du texte, ni au début).
7. Ne parle jamais en Anglais sauf si on te le demande sinon que en français
8. Ne mentionne jamais que tu es un assistant ou une IA.
9. Ne parle jamais de l'ISEN Ouest comme d'une école d'ingénieurs, mais plutôt comme d'une école d'ingénieurs généraliste.
10.L'expéditeur n'est pas un éléve"""

            response = client_ai.chat.completions.create(
                model="gemma:2b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Objectif et détails de l'e-mail : {instructions}"}
                ],
                temperature=0.7, 
                max_tokens=400
            )

            raw_content = response.choices[0].message.content.strip()
            
            cleaned_body = re.sub(r'\[(SUJET|TITRE|CORPS|BOUTON)\]:?', '', raw_content, flags=re.IGNORECASE).strip()
            cleaned_body = cleaned_body.replace('**', '')

            subject = f"ISEN - {instructions[:40]}..." if instructions else "Information - ISEN"
            headline = instructions[:60] if instructions else "Invitation officielle de l'ISEN"
            cta_button = "Confirmer ma participation"

            if not cleaned_body.lower().startswith('bonjour'):
                cleaned_body = f"{salutation_prefix}\n\n{cleaned_body}"
                
            # MODIFICATION 1 : Conversion des sauts de ligne \n en balises HTML <br>
            cleaned_body = cleaned_body.replace('\n', '<br>')

            ai_result_json = {
                "subject": subject,
                "headline": headline,
                "body": cleaned_body,
                "cta_button": cta_button
            }

            isen_base64 = get_default_isen_image_base64()

            custom_image_block = ""
            if image_url and image_url.strip() != "":
                custom_image_block = f"""
                <div style="margin: 20px 0; text-align: center;">
                    <img src="{image_url}" alt="Illustration" style="max-width: 100%; height: auto; border-radius: 4px;">
                </div>
                """

            signature_isen_footer = f"""
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e0e0e0; padding-top: 20px;">
                <p style="font-size: 14px; font-weight: bold; color: #333333; margin-bottom: 10px;">L'équipe d'Isen Ouest</p>
                <img src="{isen_base64}" alt="Isen Ouest" style="max-width: 150px; height: auto; display: block; margin: 0 auto;">
            </div>
            """

            # MODIFICATION 2 : Retrait de "white-space: pre-line;" dans les balises div contenant {cleaned_body}
            if template_type == 'invitation':
                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; background-color: #ffffff; padding: 30px;">
                    <h2 style="color: #007bff; margin-top: 0; font-size: 22px;">{headline}</h2>
                    {custom_image_block}
                    <div style="color: #333333; line-height: 1.6; font-size: 15px;">{cleaned_body}</div>
                    <div style="text-align: center; margin-top: 30px; margin-bottom: 10px;">
                        <a href="https://isen-nantes.fr" style="background-color: #007bff; color: white; padding: 14px 28px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">{cta_button}</a>
                    </div>
                    {signature_isen_footer}
                </div>
                """
            elif template_type == 'newsletter':
                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ced4da; background-color: #f8f9fa; padding: 20px;">
                    <div style="background-color: #ffffff; padding: 20px; border-bottom: 3px solid #6f42c1; text-align: center;">
                        <h1 style="color: #6f42c1; margin: 0; font-size: 24px;">NEWSLETTER ISEN</h1>
                    </div>
                    <div style="background-color: #ffffff; padding: 30px; margin-top: 15px;">
                        <h2 style="color: #2c3e50; margin-top: 0; font-size: 20px; border-left: 4px solid #6f42c1; padding-left: 10px;">{headline}</h2>
                        {custom_image_block}
                        <div style="color: #495057; line-height: 1.6; font-size: 14px;">{cleaned_body}</div>
                        <div style="text-align: right; margin-top: 20px;">
                            <a href="https://isen-nantes.fr" style="color: #6f42c1; font-weight: bold; text-decoration: none;">{cta_button} &rarr;</a>
                        </div>
                        {signature_isen_footer}
                    </div>
                </div>
                """
            elif template_type == 'communique':
                html_email = f"""
                <div style="font-family: 'Times New Roman', Times, serif; max-width: 600px; margin: 0 auto; border: 1px solid #333333; background-color: #ffffff; padding: 40px;">
                    <div style="border-bottom: 1px solid #333333; padding-bottom: 15px; margin-bottom: 25px;">
                        <strong style="font-family: Arial, sans-serif; font-size: 16px; color: #333333;">COMMUNIQUÉ INSTITUTIONNEL - ISEN</strong>
                    </div>
                    <h2 style="color: #111111; font-size: 22px; margin-top: 0; font-weight: normal;">{headline}</h2>
                    <div style="color: #222222; line-height: 1.8; font-size: 16px; margin: 25px 0;">{cleaned_body}</div>
                    {custom_image_block}
                    {signature_isen_footer}
                </div>
                """
            else:
                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; background-color: #ffffff; padding: 30px;">
                    <h2 style="color: #333333; margin-top: 0; font-size: 20px; font-weight: bold;">{headline}</h2>
                    {custom_image_block}
                    <div style="color: #444444; line-height: 1.6; font-size: 14px; margin: 20px 0;">{cleaned_body}</div>
                    <div style="margin: 25px 0;">
                        <a href="https://isen-nantes.fr" style="background-color: #495057; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; font-size: 14px;">{cta_button}</a>
                    </div>
                    {signature_isen_footer}
                </div>
                """

            draft_document = {
                "created_at": datetime.datetime.utcnow(),
                "status": "draft",
                "template_type": template_type,
                "visual_assets": {"image_url": image_url},
                "attachments": attachments,
                "targeting": {"recipients_count": len(selected_recipients)},
                "brief": {
                    "instructions": instructions,
                    "tone": tone,
                    "language_level": language_level
                },
                "ai_generation": ai_result_json,
                "final_html_rendered": html_email
            }
            collection_drafts.insert_one(draft_document)

            return JsonResponse({
                'status': 'success',
                'subject': subject,
                'body': cleaned_body,
                'headline': headline,
                'cta_button': cta_button,
                'html_preview': html_email,
                'attachments_count': len(attachments)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def get_campaign_history(request):
    if request.method == 'GET':
        try:
            campaigns_cursor = collection_drafts.find().sort("_id", -1).limit(20)
            campaigns_list = []
            for doc in campaigns_cursor:
                created_at_val = doc.get("created_at")
                date_str = created_at_val.strftime("%d/%m/%Y %H:%M") if isinstance(created_at_val, datetime.datetime) else "Récemment"
                ai_gen = doc.get("ai_generation", {})
                subject = ai_gen.get("subject") or doc.get("subject") or "Sans objet"
                body_content = ai_gen.get("body") or doc.get("body_content") or ""

                campaigns_list.append({
                    "id": str(doc.get("_id")),
                    "subject": subject,
                    "template_type": doc.get("template_type", "invitation"),
                    "created_at": date_str,
                    "body_content": body_content
                })
            return JsonResponse({'status': 'success', 'campaigns': campaigns_list})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def send_campaign_brevo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipients = data.get('recipients', [])
            subject = data.get('subject', 'Campagne ISEN')
            html_content = data.get('html_content', '')
            attachments = data.get('attachments', [])

            if not recipients:
                return JsonResponse({'status': 'error', 'error': "Aucun destinataire sélectionné."}, status=400)

            to_list = [{"email": email} for email in recipients]

            brevo_payload = {
                "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
                "to": to_list,
                "subject": subject,
                "htmlContent": html_content
            }

            if attachments:
                brevo_attachments = []
                for att in attachments:
                    base64_content = att['data'].split(",")[1] if "," in att['data'] else att['data']
                    brevo_attachments.append({"name": att['name'], "content": base64_content})
                brevo_payload["attachment"] = brevo_attachments

            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json"
            }

            response = requests.post("https://api.brevo.com/v3/smtp/email", json=brevo_payload, headers=headers)

            if response.status_code in [200, 201]:
                return JsonResponse({'status': 'success', 'message': "Campagne envoyée avec succès!"})
            else:
                return JsonResponse({'status': 'error', 'error': f"Erreur Brevo : {response.text}"}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)