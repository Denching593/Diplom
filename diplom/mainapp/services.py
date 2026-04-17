import os

import requests
from dotenv import load_dotenv

load_dotenv()
def get_dishes_by_params(cousine):
    url = 'https://api.spoonacular.com/recipes/complexSearch'
    params = {
        "apiKey": os.getenv("Apikey"),
        "number": 10,
        "cuisine": "Eastern European",
    "addRecipeInformation": True,
    "addRecipeNutrition": True

          }
    response = requests.get(url , params = params)
    if response.status_code == 200:
        data = response.json()
        recipes = data.get("results", [])

        print(f"\nНайдено рецептов: {len(recipes)}\n")

        for i, recipe in enumerate(recipes, start=1):
            name = recipe.get("title", "Без названия")
            recipe_id = recipe.get("id", "Нет ID")
            image = recipe.get("image", "Нет изображения")
            description = recipe.get("summary", "Нет описания")
            calories = "Нет данных"
            nutrients = recipe.get("nutrition", {}).get("nutrients", [])

            for n in nutrients:
                if n.get("name") == "Calories":
                    calories = int(n.get("amount"))
                    break
            print(f"🍽️ Рецепт #{i}")
            print(f"Название: {name}")
            print(f"ID: {recipe_id}")
            print(f"Описание: {description}")
            print(f"Картинка: {image}")
            print(f"Калории: {calories} ккал")
            print("-" * 40)
        return recipes
    else:
        print("Ошибка:", response.status_code, response.text)