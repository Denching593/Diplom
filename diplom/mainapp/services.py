import os
import time

import requests


def get_dishes_by_params(cousine):
    url = 'https://api.spoonacular.com/recipes/complexSearch'
    params = {
        "apiKey": os.getenv("SPOONACULAR_API_KEY"),
        "number": 10,
        "cuisine": cousine,
        "addRecipeInformation": True,
        "addRecipeNutrition": True
    }
    
    # Robust request with increased timeout for mobile networks and detailed error logging
    for attempt in range(3):
        try:
            # Increased timeout: 15 seconds connect, 30 seconds read
            response = requests.get(url, params=params, timeout=(30, 60))
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
                print(f"Ошибка API (попытка {attempt + 1}): {response.status_code}, {response.text[:100]}")
                if attempt < 2:
                    time.sleep(2)  # Increased delay between retries
        except requests.exceptions.Timeout as e:
            print(f"Таймаут запроса к Spoonacular (попытка {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except requests.exceptions.ConnectionError as e:
            print(f"Ошибка подключения к Spoonacular (попытка {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"Общая ошибка запроса к Spoonacular (попытка {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2)
    
    # Fallback: return empty list on total failure
    print("⚠️ Все попытки запроса к Spoonacular провалились. Возвращаю пустой список.")
    return []