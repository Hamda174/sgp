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
import difflib





app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the Risk Rate API!"

def normalize(text):
    return str(text).lower().strip().replace("-", "").replace(" ", "")




app = Flask(__name__)
geolocator = Nominatim(user_agent="risk-api")

# Utility
def normalize(text):
    return str(text).lower().strip().replace("-", "").replace(" ", "")

# Load JSON data
with open("cafeterias.json") as f:
    cafeterias = json.load(f)

with open("buildingMaintenance.json") as f:
    buildingMaintenance = json.load(f)

# Fuzzy matcher
def find_best_match(region, dataset):
    all_locations = [normalize(item['location']) for item in dataset if item.get('location')]
    matches = difflib.get_close_matches(normalize(region), all_locations, n=1, cutoff=0.6)
    return matches[0] if matches else None

@app.route('/get_risk_rate', methods=['POST'])
def get_risk_rate():
    try:
        data = request.get_json(force=True)
        lat = data.get('latitude')
        lng = data.get('longitude')
        activity_name = data.get('type', '').strip().lower()  # 👈 same as "name" in JSON

        if lat is None or lng is None:
            return jsonify({'error': 'Missing latitude or longitude'}), 400

        if not activity_name:
            return jsonify({'error': 'Missing type'}), 400

        # Combine both datasets
        combined_data = cafeterias + buildingMaintenance

        # Reverse geocode
        location = geolocator.reverse((lat, lng), language='en')
        if not location:
            return jsonify({'risk_rate': 0})

        address = location.raw.get('address', {})
        region_raw = (
            address.get('suburb') or
            address.get('neighbourhood') or
            address.get('city_district') or
            address.get('city') or
            address.get('state')
        )

        if not region_raw:
            return jsonify({'risk_rate': 0})

        region = normalize(region_raw)
        print(f"📍 Region: {region}, Activity: {activity_name}")

        # Fuzzy match region
        best_region_match = find_best_match(region, combined_data)
        if not best_region_match:
            return jsonify({'risk_rate': 0})

        # Match both region and name
        for item in combined_data:
            if (normalize(item['location']) == best_region_match and
                normalize(item['name']) == activity_name):
                return jsonify({
                    'name': item['name'],
                    'location': item['location'],
                    'risk_rate': item['risk_rate']
                })

        return jsonify({'risk_rate': 0})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500









        

        # Match with your cafeterias data
        #for c in cafeterias:
            #cafeteria_location = c.get('location')
            #if cafeteria_location and isinstance(cafeteria_location, str):
                #if cafeteria_location.strip().lower() == region:
                    #print(f"✅ Matched: {c['name']} in {region}")
                    #return jsonify({
                        #'name': c['name'],
                        #'location': c['location'],
                        #'risk_rate': c['risk_rate']
                    #})


        #print("❌ No match found for region")
        #return jsonify({'risk_rate': 0})

    #except Exception as e:
        #print(f"🔥 ERROR: {str(e)}")
        #return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)









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



        


@app.route("/process", methods=['GET'])
def get_data():
    result = process_data()
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
