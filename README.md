# Tempo — Gestion des emplois du temps

Tableau de bord local en français pour organiser les séances d'un établissement scolaire. L'application utilise Streamlit pour l'interface et SQLite pour conserver les données dans `emploi_du_temps.db`.

## Fonctionnalités

- Vue hebdomadaire filtrable par classe, enseignant, salle et jour.
- Gestion des classes, enseignants, salles et matières.
- Ajout et suppression des séances avec vérification automatique des chevauchements de classe, enseignant ou salle.
- Indicateurs de volume horaire et export CSV de la sélection affichée.
- Jeu de données de démonstration créé automatiquement au premier lancement.

## Lancer l'application

Python 3.11 ou une version plus récente est recommandé.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Ouvrir ensuite l'adresse locale affichée par Streamlit dans le terminal. La base SQLite est créée à côté de `app.py`. Ne supprimez pas `emploi_du_temps.db` si vous souhaitez conserver les données.

## Tests

```powershell
python -m unittest discover -s tests -v
```