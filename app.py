# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from geopy.geocoders import Nominatim
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the Risk Rate API!"

def normalize(text):
    return text.lower().replace(" ", "").replace("-", "")


street_region_df = pd.read_csv("https://docs.google.com/spreadsheets/d/e/2PACX-1vQ7V7I6YvF0virS2ZD-7r7HLFTEzz1IiEZWJK3na61qphK98-DmvE7NNUCfZO52tippTRFT_p4bc9B-/pub?output=csv")


# Create dictionary: {normalized_street: region}
street_to_region = {
    str(street).lower().strip().replace("-", "").replace(" ", ""): region.strip()
    for street, region in zip(street_region_df["Street"], street_region_df["Region"])
    if isinstance(street, str) and isinstance(region, str)
}




# Alias mapping
region_aliases = {
    "alkharan": "Al Kharan",
    # ... include all your region mappings here ...
    "almaemura": "Almaemura",
    "aljazirah": "Aljazirah",
    "alhamra": "Alhamra",
    "alqasidat": "Alqasidat",
    "alrafaea": "Alrafaea",
    "alkharran": "Al Kharran",
    "aldhaitjanoobi": "AL DHAIT JANOOBI",
    "dhehanzone": "DHEHAN ZONE",
    "ghil": "Ghil",
    "alnakeel": "Alnakeel",
    "dhait": "Dhait",
    "aldaqdaqa": "Aldaqdaqa",
    "julphar": "Julphar",
    "saihalghib": "Saih al-Ghib",
    "almairid": "Al-Mairid",
    "aljawis": "Aljawis",
    "alrams": "Alrams",
    "shaml": "Shaml",
    "udhin": "Udhin",
    "wadikub": "Wadi kub",
    "rasalkhaimah": "Ras al-Khaimah",
    "khuzam": "Khuzam",
    "shaam": "Sha'am",
    "khalifabinzayedcity": "Khalifa Bin Zayed City",
    "cornish": "CORNISH",
    "qwasim": "QWASIM",
    "sedro": "sedro",
    "sohila": "SOHILA",
    "masafi": "Masafi",
    "oraibi": "Oraibi",
    "daih": "Daih",
    "butain": "Butain",
    "samer": "Samer",
    "saqrmohammed": "Saqr Mohammed",
    "aldifan": "Aldifan",
    "alhuwailat": "Al-Huwailat",
    "alfiliya": "Alfiliya",
    "alghib": "Al-Ghib",
    "syhalqasidat": "Syh alqasidat",
    "dafta": "Dafta",
    "hodyba": "HODYBA",
    "hamraniya": "Hamraniya",
    "shawka": "shawka",
    "shmali": "SHMALI",
    "almudafaq": "Almudafaq",
    "jeer": "jeer",
    "newraskhaimah": "NEW RAS KHAIMAH",
    "glilah": "Glilah",
    "menaiharea": "MENAIH AREA",
    "alshaaghi": "Alshaaghi",
    "fahlain": "FAHLAIN",
    "dafannakheel": "Dafan Nakheel",
    "khorkhuwair": "Khor Khuwair",
    "alearibi": "alearibi",
    "alhayl": "Alhayl",
    "dehan": "DEHAN",
    "sharqya": "SHARQYA",
    "nadya": "NADYA",
    "wadiqoor": "WADI QOOR",
    "khat": "Khat",
    "amearij": "Am earij",
    "alharaf": "alharaf",
    "asfni": "Asfni",
    "alaeem": "al aeem",
    "asimah": "Asimah",
    "sihalbanh": "SIH ALBANH",
    "alsalihia": "Alsalihia",
    "aleurqub": "Aleurqub",
    "almunayi": "Al-Munayi",
    "zaid": "Zaid",
    "gueddar": "Gueddar",
    "sayhalbir": "Sayh albir",
    "alsaedy": "Alsaedy",
    "alsawan": "Alsawan",
    "almowuha": "ALMOWUHA",
    "mazraa": "Mazraa",
    "almathlutha": "Almathlutha",
    "kabdah": "Kabdah",
    "aleashish": "Aleashish",
    "mohammedbinzayedcity": "MOHAMMED BIN ZAYED CITY",
    "shehah": "Shehah",
    "ejeili": "Ejeili",
    "رأسالخيمة": "Ras al-Khaimah"
}

def normalize(text):
    return text.lower().replace(" ", "").replace("-", "").replace("ـ", "")  # Remove Arabic tatweel


# Function to fetch and process dataset
def process_data():
    file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnH-_FyYUJ5NCF_HHQjT1JhCGl7MsMxRlsRWVib3wi7P78LHuDgkLk2RwjlcuXNQ/pub?output=csv"

    try:
        df = pd.read_csv(file_url)
        print("CSV Data Loaded Successfully!")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []

    columns_to_extract = ['LicenseStatus', 'ActivityMainGroup', 'MainActivity', 'Street', 'Region', 'LastApplicationNo', 'Numberofrenewals']
    df = df[columns_to_extract]

    def label_row(row):
        if row['Numberofrenewals'] >= 3 and row['LicenseStatus'] in ['Active', 'Expired']:
            return 'high success'
        elif row['Numberofrenewals'] < 3 and row['LicenseStatus'] in ['Active', 'Expired']:
            return 'low success'
        elif row['Numberofrenewals'] >= 3 and row['LicenseStatus'] in ['Canceled', 'Totally Blocked', 'Managerially Canceled', 'Mortgaged', 'Partially Blocked', 'Suspended']:
            return 'good cancel'
        elif row['Numberofrenewals'] < 3 and row['LicenseStatus'] in ['Canceled', 'Totally Blocked', 'Managerially Canceled', 'Mortgaged', 'Partially Blocked', 'Suspended']:
            return 'bad cancel'
        elif row['LicenseStatus'] == 'Inactive':
            return 'new'
        else:
            return 'other'

    df['label'] = df.apply(label_row, axis=1)

    # Encode and cluster
    clustering_columns = ['MainActivity', 'Region']
    df_cluster = df[clustering_columns].copy()

    for col in clustering_columns:
        le = LabelEncoder()
        df_cluster[col] = le.fit_transform(df_cluster[col])

    df_cluster['Cluster'] = df_cluster.groupby('MainActivity').ngroup()
    df['Cluster'] = df_cluster['Cluster']

    # Risk scoring
    label_values = {'high success': 4, 'low success': 3, 'good cancel': 2, 'bad cancel': 1, 'new': 0}
    risk_df = df.groupby(['MainActivity', 'Region', 'label']).size().unstack(fill_value=0)

    for label in label_values:
        if label not in risk_df:
            risk_df[label] = 0

    # Calculate risk score using the given formula
    risk_df['RiskRate'] =   ( 1 - ((
    risk_df['high success'] * 4 +
    risk_df['low success'] * 3 +
    risk_df['good cancel'] * 2 +
    risk_df['bad cancel'] * 1 +
    risk_df['new'] * 0
    ) / (100 * 4)) ) * 100


    df = df.merge(risk_df[['RiskRate']], on=['MainActivity', 'Region'], how='left')
    df_clean = df.dropna()
    return df_clean[['MainActivity', 'Region', 'RiskRate']].to_dict(orient='records')

# Region resolver
def get_region_from_latlng(latitude, longitude):
    geolocator = Nominatim(user_agent="risk_rate_app")

    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location and location.raw.get("address"):
            address = location.raw["address"]
            street = address.get("road") or address.get("street")

            if street:
                normalized_street = street.lower().strip().replace("-", "").replace(" ", "")
                mapped_region = street_to_region.get(normalized_street)
                if mapped_region:
                    print(f"✅ Mapped street '{street}' to region '{mapped_region}'")
                    return mapped_region

            # fallback to region/city if street not mapped
            possible_fields = ["suburb", "neighbourhood", "city", "region", "state"]
            for field in possible_fields:
                raw_value = address.get(field)
                if raw_value:
                    return region_aliases.get(normalize(raw_value), raw_value)

    except Exception as e:
        print(f"Geocoding error: {e}")

    return "Unknown Region"

    
    print(f"🛣️ Street from geocoder: {street}")
    print(f"Normalized: {normalized_street}")
    print(f"Resolved region from mapping: {mapped_region}")



@app.route("/get_risk_rate", methods=["GET"])
def get_risk_rate():
    latitude = request.args.get("latitude", type=float)
    longitude = request.args.get("longitude", type=float)

    try:
        print(f"Request: lat={latitude}, lng={longitude}")
        region = get_region_from_latlng(latitude, longitude)
        print(f"Resolved region: {region}")

        risk_data = process_data()

        for entry in risk_data:
            if normalize(entry['Region']) == normalize(region):
                print(f"Matched region: {entry['Region']} => RiskRate: {entry['RiskRate']}")
                return jsonify({
                    "latitude": latitude,
                    "longitude": longitude,
                    "risk_rate": entry['RiskRate']
                })

        print("No match found, returning risk_rate: 0")
        return jsonify({
            "latitude": latitude,
            "longitude": longitude,
            "risk_rate": 0
        })

    except Exception as e:
        print(f"🔥 Error in /get_risk_rate: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/process", methods=['GET'])
def get_data():
    result = process_data()
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
