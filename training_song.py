import gspread
from google.oauth2 import service_account
import pandas as pd
import numpy as np
from datetime import timedelta
import locale
import os
import json
from flask import Flask, jsonify

app = Flask(__name__)

# 📌 Connexion à Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Charger la clé API depuis la variable d'environnement
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if credentials_json:
    credentials_info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=scope)
    client = gspread.authorize(creds)
else:
    raise ValueError("Clé Google Cloud manquante !")

# Process finished with exit code 1
SHEET_ID = "11nPts_8ExvcNASZA8rErLeibu6BssicQ_O0tB6Fpb9s"
sheet = client.open_by_key(SHEET_ID).worksheet("NOPLP")

# 📌 Charger les données dans un DataFrame Pandas
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Fonction pour remplacer les mois et jours français par leurs équivalents anglais
def convert_french_to_english(date_str):
    french_days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
    english_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    french_months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
    english_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    for i in range(7):
        date_str = date_str.replace(french_days[i], english_days[i])
    for i in range(12):
        date_str = date_str.replace(french_months[i], english_months[i])

    return date_str

# 📌 Prétraiter les données
def preprocess_data(df):
    locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')

    df['Date'] = df['Date'].apply(lambda x: convert_french_to_english(x))
    df['Date'] = pd.to_datetime(df['Date'], format='%A %d %B %Y')

    title_data, artist_data = {}, {}
    for _, row in df.iterrows():
        title, artist, date = row['Titre'], row['Artiste'], row['Date']
        title_data.setdefault(title, []).append(date)
        artist_data.setdefault(artist, []).append(date)

    return title_data, artist_data

title_data, artist_data = preprocess_data(df)

# 📌 Calcul des moyennes des écarts entre passages
def calculate_mean_intervals(data):
    mean_intervals = {}
    for key, dates in data.items():
        sorted_dates = sorted(dates)
        intervals = [(sorted_dates[i] - sorted_dates[i - 1]).days for i in range(1, len(sorted_dates))]
        mean_intervals[key] = np.mean(intervals) if intervals else None
    return mean_intervals

title_mean_intervals = calculate_mean_intervals(title_data)
artist_mean_intervals = calculate_mean_intervals(artist_data)

# 📌 Calcul des rappels
def calculate_review_levels(mean_intervals):
    levels = {}
    for key, mean in mean_intervals.items():
        if mean is not None:
            levels[key] = {
                'niveau_1': mean * 0.75,
                'niveau_2': mean * 0.90,
                'niveau_3': mean,
                'niveau_4': mean * 1.10,
                'niveau_5': mean * 1.25
            }
        else:
            levels[key] = None
    return levels

title_review_levels = calculate_review_levels(title_mean_intervals)
artist_review_levels = calculate_review_levels(artist_mean_intervals)

# 📌 Routes Flask
@app.route('/')
def index():
    return "L'application fonctionne avec Google Sheets !"

@app.route('/rappels_titres')
def rappels_titres():
    return jsonify(title_review_levels)

@app.route('/rappels_artistes')
def rappels_artistes():
    return jsonify(artist_review_levels)

# 📌 Ajouter une nouvelle chanson dans Google Sheets
@app.route('/ajouter/<titre>/<artiste>/<date>')
def ajouter_chanson(titre, artiste, date):
    # Ajouter la chanson à la feuille Google Sheet
    sheet.append_row([date, titre, artiste, "Classique", "Chanson à point", "Oui"])  # Ajoute avec le bon format
    return f"Chanson ajoutée : {titre} - {artiste} ({date})"

if __name__ == '__main__':
    app.run(debug=True)
