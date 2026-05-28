import pytest
from unittest.mock import patch, MagicMock
from project_scripts.ETL.ETL_poc1 import run_pure_etl

class TestETLPoc1:
    
    @patch("project_scripts.ETL.ETL_poc1.MongoClient")
    def test_run_pure_etl_sans_modifier_la_base(self, mock_mongo_client):
        """
        Ce test lance l'ensemble du script ETL_poc1.py de manière sécurisée.
        Il lit le VRAI fichier Excel et exécute toutes les transformations,
        mais l'insertion dans MongoDB est simulée et bloquée.
        """
        
        # 1. PRÉPARATION DU BOUCLIER (MOCK)
        # On simule le comportement de client["poc_aggregation"] pour qu'il ne fasse rien
        mock_db = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db

        # 2. EXÉCUTION DU SCRIPT
        # On lance la fonction principale. Grâce au @patch au-dessus,
        # l'import de MongoClient dans le script original a été remplacé par notre faux objet.
        run_pure_etl()

        # 3. VÉRIFICATIONS AUTOMATIQUES
        # On s'assure que le script a bien tenté de se connecter au bon endroit
        mock_mongo_client.assert_called_once_with("mongodb://localhost:27018/")

        # On vérifie que les opérations de nettoyage (delete_many) ont bien été appelées
        # sur les fausses collections
        assert mock_db["prospects_bruts"].delete_many.called, "Les anciennes fiches brutes auraient dû être effacées."
        assert mock_db["prospects_taxe"].delete_many.called, "Les anciennes fiches taxe auraient dû être effacées."
        
        # On vérifie que le script a bien tenté d'insérer des données (insert_many)
        # Si ça passe, c'est que l'Excel a bien été lu et transformé !
        assert mock_db["prospects_bruts"].insert_many.called, "L'insertion des fiches brutes n'a pas eu lieu."
        assert mock_db["prospects_taxe"].insert_many.called, "L'insertion des fiches taxe n'a pas eu lieu."
        assert mock_db["prospects_emailing"].insert_many.called, "L'insertion des fiches emailing n'a pas eu lieu."