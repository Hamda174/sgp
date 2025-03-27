# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from geopy.geocoders import Nominatim
import os
import json
import re
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


with open("street_to_region_alias_with_variations.json") as f:
    street_region_map = json.load(f)
with open("region_aliases.json") as f:
    region_aliases = json.load(f)


app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the Risk Rate API!"

def normalize(text):
    return str(text).lower().strip().replace("-", "").replace(" ", "")



# Load your dataset
file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnH-_FyYUJ5NCF_HHQjT1JhCGl7MsMxRlsRWVib3wi7P78LHuDgkLk2RwjlcuXNQ/pub?output=csv"
df = pd.read_csv(file_url)

# Filter for cafes
cafes = df[df['MainActivity'].str.lower() == 'cafe'].copy()
cafes['FullAddress'] = cafes['Street'].fillna('') + ', ' + cafes['Region'].fillna('')

# Setup geocoder
geolocator = Nominatim(user_agent="cafe_mapper")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# Geocode
cafes['Location'] = cafes['FullAddress'].apply(geocode)
cafes['Latitude'] = cafes['Location'].apply(lambda loc: loc.latitude if loc else None)
cafes['Longitude'] = cafes['Location'].apply(lambda loc: loc.longitude if loc else None)

# Save it
cafes_clean = cafes.dropna(subset=["Latitude", "Longitude"])
cafes_clean[['MainActivity', 'Street', 'Region', 'Latitude', 'Longitude']].to_csv("cafe_dataset_geocoded.csv", index=False)


@app.route("/get_all_cafes", methods=["GET"])
def get_all_cafes():
    try:
        df = pd.read_csv("cafe_dataset_geocoded.csv")
        result = df.to_dict(orient="records")
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500








file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRnH-_FyYUJ5NCF_HHQjT1JhCGl7MsMxRlsRWVib3wi7P78LHuDgkLk2RwjlcuXNQ/pub?output=csv"

try:
    # Attempt to read the file
    df = pd.read_csv(file_url)
    print("CSV file loaded successfully.")
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit()


# Select only the required columns
columns_to_extract = ['LicenseStatus', 'ActivityMainGroup', 'MainActivity', 'Street', 'Region', 'LastApplicationNo', 'Numberofrenewals']
df = df[columns_to_extract]

# Define the labeling logic
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
        return 'other'  # Optional: To handle cases that don't match any condition

# Apply the labeling function
df['label'] = df.apply(label_row, axis=1)

# Display the updated DataFrame
print(df[['LicenseStatus', 'Numberofrenewals', 'label']])  # Showing only relevant columns for clarity

clustering_columns = ['MainActivity', 'Region']
df_cluster = df[clustering_columns].copy()

# Step 2: Convert categorical variables to numerical using Label Encoding
label_encoders = {}
for col in clustering_columns:
    le = LabelEncoder()
    df_cluster[col] = le.fit_transform(df_cluster[col])  # Convert text to numbers
    label_encoders[col] = le  # Store encoders for later decoding if needed


# Step 3: Assign a unique cluster number for each unique MainActivity
df_cluster['Cluster'] = df_cluster.groupby('MainActivity').ngroup()

# Step 4: Merge clustering results back to the original dataset
df['Cluster'] = df_cluster['Cluster']

# Step 6: Display results
print(df[['MainActivity', 'Region', 'Cluster']])



# Define label values
label_values = {
    'high success': 4,
    'low success': 3,
    'good cancel': 2,
    'bad cancel': 1,
    'new': 0
}

# Group by MainActivity and Region, count the occurrences of each label
risk_df = df.groupby(['MainActivity', 'Region', 'label']).size().unstack(fill_value=0)


# Ensure all label categories exist
for label in label_values.keys():
    if label not in risk_df.columns:
        risk_df[label] = 0

# Calculate risk score using the given formula
risk_df['RiskRate'] =   ( 1 - ((
    risk_df['high success'] * 4 +
    risk_df['low success'] * 3 +
    risk_df['good cancel'] * 2 +
    risk_df['bad cancel'] * 1 +
    risk_df['new'] * 0
) / (100 * 4)) ) * 100


# Merge back into original DataFrame
df = df.merge(risk_df[['RiskRate']], on=['MainActivity', 'Region'], how='left')

# Display results
print(df[['MainActivity', 'Region', 'RiskRate']])

df_clean = df.dropna()
print(df_clean[['MainActivity', 'Region', 'RiskRate']])

# Convert to DataFrame
df = pd.DataFrame(df_clean)

def normalize(text):
    return str(text).lower().strip().replace("-", "").replace(" ", "")


@app.route('/get_risk_rate', methods=['POST'])
def get_risk_rate():
    data = request.get_json()
    main_activity = normalize(data.get("MainActivity"))

    region = normalize(data.get("Region"))
    region = region_aliases.get(region, region)
    
    street = data.get("Street")
    if street:
        street_norm = normalize(street)
        corrected_region = street_region_map.get(street_norm)
        if corrected_region:
            region = normalize(corrected_region) 
            print(f"Mapped street '{street}' to region '{corrected_region}'")
            
    # If alias match fails, do a fuzzy search
    if not corrected_region:
        import difflib
        closest_match = difflib.get_close_matches(street_norm, street_region_map.keys(), n=1, cutoff=0.8)
        if closest_match:
            corrected_region = street_region_map[closest_match[0]]
            region = normalize(corrected_region)
            print(f"Fuzzy matched '{street}' to region '{corrected_region}'")



    print(f"Incoming: activity={main_activity}, region={region}, street={street}")


    df['MainActivity_norm'] = df['MainActivity'].apply(normalize)
    df['Region_norm'] = df['Region'].apply(normalize)

    match = df[
        df['Region_norm'].str.contains(region) &
        df['MainActivity_norm'].str.contains(main_activity)
    ]
    
    print(f"Mapped street '{street}' to region '{corrected_region}'")

    if not match.empty:
        risk_rate = match['RiskRate'].iloc[0]
        return jsonify({'RiskRate': round(risk_rate, 2)})
    else:
        return jsonify({'RiskRate': None, 'message': 'No match found'}), 404
        


@app.route("/process", methods=['GET'])
def get_data():
    result = process_data()
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
