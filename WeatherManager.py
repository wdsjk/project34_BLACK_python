import requests
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound, TooManyRequests


class WeatherManager:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_weather_data(self, location, interval):
        coords = self.get_lat_lon(location)

        lat = coords["lat"]
        lon = coords["lon"]
        cnt = 8 * interval

        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&cnt={cnt}&units=metric&appid={self.api_key}"

        r = requests.get(url)

        if r.status_code != 200:
            match r.status_code:
                case 400:
                    raise BadRequest(f"Bad Request error {r.status_code}: {r.json()}")
                case 401:
                    raise Unauthorized(f"Unauthorized error {r.status_code}: {r.json()}")
                case 404:
                    raise NotFound(f"Not Found error {r.status_code}: {r.json()}")
                case 429:
                    raise TooManyRequests(f"Too Many Requests error {r.status_code}: {r.json()}")
                case _:
                    raise Exception(f"Unexpected error {r.status_code}: {r.json()}")

        response = r.json()
        data = {}

        for weather_data in response["list"]:
            if weather_data["dt_txt"].split()[0] not in data.keys():
                if len(data.keys()) == interval:
                    break

                data[weather_data["dt_txt"].split()[0]] = {
                    "temperature": [weather_data["main"]["temp"]],
                    "wind_speed": [weather_data["wind"]["speed"]],
                    "precipitation": [weather_data["weather"][0]["main"]]
                }
            else:
                data[weather_data["dt_txt"].split()[0]]["temperature"].append(weather_data["main"]["temp"])
                data[weather_data["dt_txt"].split()[0]]["wind_speed"].append(weather_data["wind"]["speed"])

                if weather_data["weather"][0]["main"] not in data[weather_data["dt_txt"].split()[0]]["precipitation"]:
                    data[weather_data["dt_txt"].split()[0]]["precipitation"].append(weather_data["weather"][0]["main"])

        for date in data.keys():
            data[date]["temperature"] = round(sum(data[date]["temperature"]) / len(data[date]["temperature"]), 2)
            data[date]["wind_speed"] = round(sum(data[date]["wind_speed"]) / len(data[date]["wind_speed"]), 2)

        return data

    def get_lat_lon(self, location):
        url_for_location = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&appid={self.api_key}"

        r = requests.get(url_for_location)

        if r.status_code != 200:
            raise Exception(f"Unexpected error {r.status_code}: {r.json()}")

        response = r.json()

        if not response:
            raise NotFound(f"City is not found: {location}")

        return {
            "lat": response[0]["lat"],
            "lon": response[0]["lon"]
        }