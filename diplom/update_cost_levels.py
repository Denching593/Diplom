"""
Скрипт для распределения рецептов по уровням стоимости.
Запускать после добавления поля cost_level.

Эконом (1): простые блюда из дешёвых ингредиентов (каши, супы, яичница)
Средний (2): обычные блюда (курица, паста, салаты)
Премиум (3): блюда с дорогими ингредиентами (стейки, морепродукты, деликатесы)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diplom.settings')
django.setup()

from mainapp.models import Recipes

# Словарь ключевых слов для определения уровня стоимости
economy_keywords = ['каш', 'овсянк', 'гречк', 'рис', 'суп', 'борщ', 'яичн', 'омлет', 
                    'макарон', 'картошк', 'пшен', 'манн', 'геркулес', 'бутерброд',
                    'гренк', 'драник', 'оладь', 'блин', 'лапш']

premium_keywords = ['стейк', 'лосось', 'семга', 'тунец', 'креветк', 'миди', 'икр',
                    'говядин', 'баранин', 'филе', 'парм', 'прошут', 'деликат',
                    'морепродукт', 'рибай', 'филе миньон', 'карпаччо', 'трюфел']


def classify_recipe(recipe_name):
    """Определяет уровень стоимости рецепта по названию."""
    name_lower = recipe_name.lower()
    
    # Проверяем премиум ключевые слова
    for keyword in premium_keywords:
        if keyword in name_lower:
            return 3
    
    # Проверяем эконом ключевые слова
    for keyword in economy_keywords:
        if keyword in name_lower:
            return 1
    
    # Всё остальное - средний уровень
    return 2


def update_cost_levels():
    """Обновляет cost_level для всех рецептов."""
    recipes = Recipes.objects.all()
    
    economy_count = 0
    medium_count = 0
    premium_count = 0
    
    for recipe in recipes:
        old_cost_level = recipe.cost_level
        new_cost_level = classify_recipe(recipe.name)
        
        recipe.cost_level = new_cost_level
        recipe.save()
        
        if new_cost_level == 1:
            economy_count += 1
        elif new_cost_level == 2:
            medium_count += 1
        else:
            premium_count += 1
        
        if old_cost_level != new_cost_level:
            print(f"Обновлено: {recipe.name} -> {new_cost_level} ({'Эконом' if new_cost_level == 1 else 'Премиум' if new_cost_level == 3 else 'Средний'})")
    
    print(f"\n=== ИТОГО ===")
    print(f"Эконом (1): {economy_count}")
    print(f"Средний (2): {medium_count}")
    print(f"Премиум (3): {premium_count}")
    print(f"Всего рецептов: {recipes.count()}")


if __name__ == '__main__':
    update_cost_levels()
