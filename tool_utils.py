from langchain.tools import tool
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import requests
import os
from dotenv import load_dotenv
load_dotenv()

@tool
def geocode_address(address: str) -> str:
    """Geocodes a given address and returns its latitude, longitude, and formatted address."""
    geolocator = Nominatim(user_agent="geo_agent")
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return f"Latitude: {location.latitude}, Longitude: {location.longitude}, Address: {location.address}"
        else:
            return "No result found."
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return f"Geocoding error: {str(e)}"


@tool
def get_solar_resource(lat_lon: str) -> str:
    """
    Fetches solar resource data (e.g., average DNI) from the NREL Solar Resource API.
    Input must be a comma-separated latitude and longitude string (e.g., "34.05,-118.25").
    """
    try:
        lat, lon = map(str.strip, lat_lon.split(","))
        api_key = os.getenv("NREL_API_KEY")  # Replace with your NREL API key
        url = "https://developer.nrel.gov/api/solar/solar_resource/v1.json"
        params = {"api_key": api_key, "lat": lat, "lon": lon}

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Extract key solar resource values
        dni = data["outputs"]["avg_dni"]["annual"]
        return (
            f"At latitude {lat} and longitude {lon}:\n"
            f"- Annual Average DNI: {dni} kWh/m²/day\n"
        )

    except Exception as e:
        return f"Error retrieving solar data: {e}"
