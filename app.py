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

# 🟢 Define a function to process and return risk rates
def process_data():
    file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnH-_FyYUJ5NCF_HHQjT1JhCGl7MsMxRlsRWVib3wi7P78LHuDgkLk2RwjlcuXNQ/pub?output=csv"

    try:
        df = pd.read_csv(file_url)
    except Exception as e:
        return {"error": f"Error loading CSV: {e}"}

    # Keep relevant columns
    columns_to_extract = ['LicenseStatus', 'ActivityMainGroup', 'MainActivity', 'Street', 'Region', 'LastApplicationNo', 'Numberofrenewals']
    df = df[columns_to_extract]

    # Assign labels
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

    # Encode categorical columns
    clustering_columns = ['MainActivity', 'Region']
    df_cluster = df[clustering_columns].copy()
    label_encoders = {}

    for col in clustering_columns:
        le = LabelEncoder()
        df_cluster[col] = le.fit_transform(df_cluster[col])
        label_encoders[col] = le

    df_cluster['Cluster'] = df_cluster.groupby('MainActivity').ngroup()
    df['Cluster'] = df_cluster['Cluster']

    # Assign risk scores
    label_values = {'high success': 4, 'low success': 3, 'good cancel': 2, 'bad cancel': 1, 'new': 0}
    risk_df = df.groupby(['MainActivity', 'Region', 'label']).size().unstack(fill_value=0)

    for label in label_values.keys():
        if label not in risk_df.columns:
            risk_df[label] = 0

    risk_df['RiskRate'] = (1 - ((
        risk_df['high success'] * 4 +
        risk_df['low success'] * 3 +
        risk_df['good cancel'] * 2 +
        risk_df['bad cancel'] * 1 +
        risk_df['new'] * 0
    ) / (100 * 4))) * 100

    df = df.merge(risk_df[['RiskRate']], on=['MainActivity', 'Region'], how='left')
    df_clean = df.dropna()

    # Return as JSON
    return df_clean[['MainActivity', 'Region', 'RiskRate']].to_dict(orient='records')

# 🟢 Define API Route to Get Risk Rate Based on Location
@app.route("/get_risk_rate", methods=["GET"])
def get_risk_rate():
    latitude = request.args.get("latitude", type=float)
    longitude = request.args.get("longitude", type=float)

    if latitude is None or longitude is None:
        return jsonify({"error": "Latitude and Longitude are required"}), 400

    # Process latest risk data
    risk_data = process_data()

    region = get_region_from_latlng(latitude, longitude)

    # Find the risk rate for the identified region
    for entry in risk_data:
        if entry["Region"] == region:
            return jsonify({"latitude": latitude, "longitude": longitude, "risk_rate": entry["RiskRate"]})

    return jsonify({"latitude": latitude, "longitude": longitude, "risk_rate": 0})  # Default

# 🟢 Mock function to calculate risk (Replace with real algorithm)

def get_region_from_latlng(latitude, longitude):
    geolocator = Nominatim(user_agent="risk_rate_app")
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location and location.raw.get("address"):
            return location.raw["address"].get("region", "Unknown Region")
    except Exception as e:
        print(f"Error in geocoding: {e}")
    return "Unknown Region"

def calculate_risk(latitude, longitude):
    region = get_region_from_latlng(latitude, longitude)
    risk_data = process_data()  # Fetch processed risk data

    for entry in risk_data:
        if entry["Region"] == region:
            return entry["RiskRate"]

    return 0  # Default if no match found


# 🟢 API Endpoint to Process Data
@app.route('/process', methods=['GET'])
def get_data():
    result = process_data()
    print(result)  # Debugging: Print processed risk data
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
