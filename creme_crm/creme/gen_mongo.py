import pymongo
from faker import Faker

fake = Faker('fr_FR')

def generate_demo_data(count=10):
    # Connexion à la base spécifique
    client = pymongo.MongoClient("mongodb://localhost:27018/") 
    db = client["poc_aggregation"]
    collection = db["prospects_bruts"]

    print(f"---  Génération de {count} prospects dans MongoDB ---")

    prospects = []
    for _ in range(count):
        prospect = {
            "prenom": fake.first_name(),
            "nom": fake.last_name(),
            "email": fake.ascii_free_email(),
            "numero_telephone": fake.phone_number(),
            "adresse": fake.address(),
            "status": "new"  
        }
        prospects.append(prospect)

    collection.insert_many(prospects)
    print(f" Succès ! {count} documents ajoutés.")

if __name__ == "__main__":
    generate_demo_data(10)