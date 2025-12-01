import os
import requests

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_weather(city: str) -> str:
    if not API_KEY:
        return "The OPENWEATHER_API_KEY is not set. Please get a key from OpenWeatherMap and set it as an environment variable."

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "imperial"  # Use Fahrenheit
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()

        main_weather = data.get("weather", [{}])[0]
        main_temp = data.get("main", {})

        description = main_weather.get("description", "N/A")
        temp = main_temp.get("temp", "N/A")
        feels_like = main_temp.get("feels_like", "N/A")

        return f"The weather in {city.title()} is currently {description} with a temperature of {temp}°F, though it feels like {feels_like}°F."

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            return f"Sorry, I couldn't find the city '{city}'. Please check the spelling and try again."
        elif response.status_code == 401:
            return "Authentication failed. Please check if your OPENWEATHER_API_KEY is correct and active."
        else:
            return f"An HTTP error occurred: {http_err}"
    except Exception as err:
        return f"An unexpected error occurred: {err}"
