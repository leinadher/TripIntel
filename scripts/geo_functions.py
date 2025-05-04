import os
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import openrouteservice
from openrouteservice import convert
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

geolocator = Nominatim(user_agent="tripintel")

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
ors_client = openrouteservice.Client(key=ORS_API_KEY)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = sin(delta_phi / 2)**2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c  # in meters

def seconds_to_hours(seconds):
    if pd.isna(seconds):
        return "-"
    return round(seconds / 3600, 2)

def meters_to_km(meters):
    if pd.isna(meters):
        return "-"
    return round(meters / 1000, 2)

def geocode_place(place_name):
    """
    Geocode a place name to (latitude, longitude) using OpenStreetMap (Nominatim)
    """
    try:
        location = geolocator.geocode(place_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

def get_route_coords(lat1, lon1, lat2, lon2, transport_mode):
    profile_map = {
        "walk": "foot-walking",
        "hike": "foot-hiking",
        "drive": "driving-car",
        "bike": "cycling-regular",
        "train": None  # handled as straight line
    }

    if transport_mode in ["fly", "train"]:
        coords = [[lon1, lat1], [lon2, lat2]]
        # Estimate straight-line distance using haversine
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        if transport_mode == "fly":
            speed_mps = 166  # 600 km/h
        elif transport_mode == "train":
            speed_mps = 542  # ~150 km/h
        duration = distance / speed_mps
        return coords, duration, distance

    profile = profile_map.get(transport_mode)
    if not profile:
        return [[lon1, lat1], [lon2, lat2]], None, None

    try:
        route = ors_client.directions(
            coordinates=[[lon1, lat1], [lon2, lat2]],
            profile=profile,
            format="geojson"
        )
        coords = route['features'][0]['geometry']['coordinates']
        summary = route['features'][0]['properties']['summary']
        return coords, summary['duration'], summary['distance']
    except Exception as e:
        print(f"Routing error: {e}")
        return [[lon1, lat1], [lon2, lat2]], None, None