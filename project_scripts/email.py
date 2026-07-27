import json
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from openai import OpenAI

# 1. Configuration pour interroger OLLAMA SUR WSL
client_ai = OpenAI(
    base_url='http://127.0.0.1:11434/v1',
    api_key='ollama'
)

# 2. Connexion à la base de données MongoDB locale (port 27018)
client_db = MongoClient('mongodb://localhost:27018/')
db = client_db['poc_aggregation']
collection_drafts = db['CampaignDraft']
collection_contacts = db['prospects_bruts']  

@csrf_exempt
def get_contacts(request):
    """
    Route API qui récupère les prospects en lisant dans les sous-groupes 
    coordonnees, contact et entite de la base poc_aggregation, avec support
    de la recherche textuelle insensibilisée à la casse.
    """
    if request.method == 'GET':
        try:
            role_query = request.GET.get('role', '')
            search_query = request.GET.get('search', '').strip()
            
            # 1. Filtre de base : les contacts autorisant l'emailing
            query = {"is_in_emailing": "OUI"}
            
            # 2. Si un terme de recherche a été saisi par l'utilisateur
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
            
            # Limitation à 100 documents pour garantir une fluidité d'affichage optimale
            contacts_cursor = collection_contacts.find(query).limit(100)
            
            contacts_list = []
            for doc in contacts_cursor:
                # Extraction de l'email depuis le sous-groupe 'coordonnees'
                coordonnees = doc.get("coordonnees") or {}
                email = coordonnees.get("email") or coordonnees.get("raw") or ""
                
                if email:
                    # Extraction du nom et prénom depuis le sous-groupe 'contact'
                    contact = doc.get("contact") or {}
                    first_name = str(contact.get("prenom", "")).strip()
                    last_name = str(contact.get("nom", "")).strip() or "Prospect"
                    
                    # Extraction de la société depuis le sous-groupe 'entite'
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
            
            # SÉCURITÉ : Si la recherche donne 0 résultat ou si aucun profil n'a le tag OUI,
            # on tente une recherche de secours sans le filtre strict is_in_emailing
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
            instructions = data.get('instructions')
            tone = data.get('tone')
            language_level = data.get('language_level')

            if not image_url or image_url.strip() == "":
                image_url = "https://via.placeholder.com/600x250/007bff/ffffff?text=ISEN+Brest+Engineering"

            if template_type == 'invitation':
                structure_demandee = """{
                  "subject": "Objet persuasif et incitatif de l'email",
                  "headline": "Grand titre principal sous la bannière",
                  "body": "Texte d'invitation complet (2 ou 3 paragraphes séparés par des sauts de ligne \\n)",
                  "cta_button": "Texte court pour le bouton d'action (ex: Confirmer ma présence)"
                }"""
            elif template_type == 'newsletter':
                structure_demandee = """{
                  "subject": "Objet informatif de la newsletter",
                  "headline": "Titre de l'article ou de la synthèse",
                  "body": "Corps complet du message séparé par des sauts de ligne \\n",
                  "cta_button": "Texte du lien d'action (ex: Lire l'article complet)"
                }"""
            else:
                structure_demandee = """{
                  "subject": "Objet formel du communiqué",
                  "headline": "Titre institutionnel de l'annonce",
                  "body": "Texte détaillé et formel séparé par des sauts de ligne \\n",
                  "cta_button": "Texte du bouton (ex: Consulter le document officiel)"
                }"""

            system_prompt = f"""Tu es l'assistant IA de rédaction expert représentant l'ISEN (20 Rue Cuirassé Bretagne, 29200 Brest).
Ta mission est de rédiger un e-mail professionnel et engageant en te basant STRICTEMENT sur les consignes données.

PARAMÈTRES DE RÉDACTION :
- Public ciblé : {target_role}
- Ton souhaité : {tone}
- Niveau de langue : {language_level}

RÈGLES IMPÉRATIVES :
1. Tu dois répondre UNIQUEMENT par un objet JSON brut, valide et sans texte autour.
2. N'invente aucune date ni aucun lieu non spécifié dans le brief.
3. Signe obligatoirement par "L'équipe ISEN".
4. Ne mets aucun symbole de type émoticône ou emoji dans le texte généré.

Le JSON doit obligatoirement respecter ce schéma exact :
{structure_demandee}"""

            response = client_ai.chat.completions.create(
                model="mistral",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Voici ma demande de rédaction : {instructions}"}
                ],
                temperature=0.7
            )

            ai_result_json = json.loads(response.choices[0].message.content)
            
            subject = ai_result_json.get("subject", "Objet non généré")
            headline = ai_result_json.get("headline", "Titre non généré")
            body = ai_result_json.get("body", "Texte non généré")
            cta_button = ai_result_json.get("cta_button", "En savoir plus")

            if template_type == 'invitation':
                html_email = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; background-color: #ffffff;">
                    <div style="text-align: center;">
                        <img src="{image_url}" alt="Bannière ISEN" style="width: 100%; max-height: 250px; object-fit: cover; display: block;">
                    </div>
                    <div style="padding: 30px;">
                        <h2 style="color: #007bff; margin-top: 0; font-size: 22px;">{headline}</h2>
                        <div style="color: #333333; line-height: 1.6; white-space: pre-line; font-size: 15px;">{body}</div>
                        <div style="text-align: center; margin-top: 30px; margin-bottom: 10px;">
                            <a href="https://isen-nantes.fr" style="background-color: #007bff; color: white; padding: 14px 28px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">{cta_button}</a>
                        </div>
                    </div>
                    <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #e0e0e0;">
                        ISEN - 20 Rue Cuirassé Bretagne, 29200 Brest<br>
                        Ce message a été généré via Crème CRM.
                    </div>
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
                        <div style="text-align: center; margin: 20px 0;">
                            <img src="{image_url}" alt="Illustration" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: 4px;">
                        </div>
                        <div style="color: #495057; line-height: 1.6; white-space: pre-line; font-size: 14px;">{body}</div>
                        <div style="text-align: right; margin-top: 20px;">
                            <a href="https://isen-nantes.fr" style="color: #6f42c1; font-weight: bold; text-decoration: none;">{cta_button} &rarr;</a>
                        </div>
                    </div>
                    <div style="text-align: center; font-size: 11px; color: #888888; margin-top: 15px;">
                        ISEN Brest - Tous droits réservés.
                    </div>
                </div>
                """
            else:
                html_email = f"""
                <div style="font-family: 'Times New Roman', Times, serif; max-width: 600px; margin: 0 auto; border: 1px solid #333333; background-color: #ffffff; padding: 40px;">
                    <div style="border-bottom: 1px solid #333333; padding-bottom: 15px; margin-bottom: 25px;">
                        <strong style="font-family: Arial, sans-serif; font-size: 16px; color: #333333;">COMMUNIQUÉ INSTITUTIONNEL - ISEN</strong>
                    </div>
                    <h2 style="color: #111111; font-size: 22px; margin-top: 0; font-weight: normal;">{headline}</h2>
                    <div style="color: #222222; line-height: 1.8; white-space: pre-line; font-size: 16px; margin: 25px 0;">{body}</div>
                    <div style="margin: 30px 0; text-align: center;">
                        <img src="{image_url}" alt="Document officiel" style="max-width: 80%; height: auto; border: 1px solid #cccccc; padding: 5px;">
                    </div>
                    <div style="margin-top: 40px; font-family: Arial, sans-serif; font-size: 14px; color: #333333;">
                        <p style="margin: 0;"><strong>{cta_button}</strong></p>
                        <p style="margin: 5px 0 0 0; font-size: 12px; color: #666666;">20 Rue Cuirassé Bretagne, 29200 Brest</p>
                    </div>
                </div>
                """

            draft_document = {
                "created_at": datetime.datetime.utcnow(),
                "status": "draft",
                "template_type": template_type,
                "visual_assets": {"image_url": image_url},
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
                'html_preview': html_email
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)