import requests

class TheMealDBClient:
    BASE_URL = "https://www.themealdb.com/api/json/v1/1/"

    def __init__(self):
        pass

    def search_meal_by_name(self, name):
        return self._get("search.php", {"s": name})

    def search_meal_by_first_letter(self, letter):
        return self._get("search.php", {"f": letter})

    def lookup_meal_by_id(self, meal_id):
        return self._get("lookup.php", {"i": meal_id})

    def random_meal(self):
        return self._get("random.php")

    def list_all_categories(self):
        return self._get("categories.php")

    def list_all_areas(self):
        return self._get("list.php", {"a": "list"})

    def list_all_ingredients(self):
        return self._get("list.php", {"i": "list"})

    def filter_by_ingredient(self, ingredient):
        return self._get("filter.php", {"i": ingredient})

    def filter_by_category(self, category):
        return self._get("filter.php", {"c": category})

    def filter_by_area(self, area):
        return self._get("filter.php", {"a": area})

    def _get(self, endpoint, params=None):
        url = self.BASE_URL + endpoint
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return None

if __name__ == "__main__":
    client = TheMealDBClient()

    # Search by name
    result = client.search_meal_by_name("Arrabiata")
    print(result)

    # Random meal
    random = client.random_meal()
    print(random["meals"][0]["strMeal"])

    # Categories
    categories = client.list_all_categories()
    for category in categories["categories"]:
        print(category["strCategory"])

    categories = client.list_all_areas()
    print(list(categories.keys()))
    for category in categories["meals"]:
        print(category)

    #print(client.list_all_ingredients())
