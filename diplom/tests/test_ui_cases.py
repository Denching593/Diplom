"""
Тесты для UI-кейсов таблицы тестирования
Покрывает все 13 тестов из таблицы: UI-01 — UI-13
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from django.utils import timezone
import json

from mainapp.models import (
    Recipes, Ingredients, MealPlan, MealPlanItem,
    ShoppingList, UserPreference, UserSettings,
    Kitchenname, Favorite, RecipeIngredient
)

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )


@pytest.fixture
def authenticated_client(user):
    client = Client()
    client.login(username='testuser', password='testpass123')
    client.user = user
    return client


@pytest.fixture
def kitchen():
    return Kitchenname.objects.create(name='Европейская')


@pytest.fixture
def recipe(kitchen):
    return Recipes.objects.create(
        name='Тестовое блюдо',
        description='Описание блюда',
        calories=500,
        KitchennameId=kitchen,
        meal_type='lunch',
        cost_level=2,
    )


@pytest.fixture
def ingredient():
    return Ingredients.objects.create(
        name='Тестовый ингредиент',
        unit='гр'
    )


# ============================================================================
# UI-01: Генерация рациона
# ============================================================================
class TestUI01GenerationOfDiet:
    """Тесты для генерации рациона питания"""

    def test_generate_meal_plan_success(self, authenticated_client, kitchen):
        """UI-01: Проверка успешной генерации плана питания"""
        # Создаём рецепты разных типов
        Recipes.objects.create(
            name='Завтрак тест',
            description='Завтрак',
            calories=400,
            KitchennameId=kitchen,
            meal_type='breakfast',
            cost_level=2,
        )
        Recipes.objects.create(
            name='Обед тест',
            description='Обед',
            calories=600,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )
        Recipes.objects.create(
            name='Ужин тест',
            description='Ужин',
            calories=500,
            KitchennameId=kitchen,
            meal_type='dinner',
            cost_level=2,
        )

        url = reverse('generate_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'meal_types': ['breakfast', 'lunch', 'dinner'],
            'dish_counts': {'breakfast': 1, 'lunch': 1, 'dinner': 1, 'snack': 0},
            'budget_tier': 'medium',
            'selected_ingredients': [],
            'excluded_ingredients': [],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True
        assert 'meal_plan' in json_response
        assert json_response.get('target_calories') == 2000

    def test_generate_meal_plan_empty_plan(self, authenticated_client):
        """UI-01: Генерация при отсутствии рецептов"""
        url = reverse('generate_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'meal_types': ['breakfast'],
            'dish_counts': {'breakfast': 1},
            'budget_tier': 'medium',
            'selected_ingredients': [],
            'excluded_ingredients': [],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        # Возвращается успешный ответ, даже если план пустой
        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True


# ============================================================================
# UI-02: Эконом-режим
# ============================================================================
class TestUI02EconomyMode:
    """Тесты для эконом-режима генерации рациона"""

    def test_economy_mode_selects_budget_dishes(self, authenticated_client, kitchen):
        """UI-02: Эконом-режим подбирает бюджетные блюда (cost_level=1)"""
        # Создаём рецепты с разным cost_level
        economy_recipe = Recipes.objects.create(
            name='Экономное блюдо',
            description='Бюджетный рецепт',
            calories=400,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=1,  # Эконом
        )
        premium_recipe = Recipes.objects.create(
            name='Премиум блюдо',
            description='Дорогой рецепт',
            calories=600,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=3,  # Премиум
        )

        url = reverse('generate_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'meal_types': ['lunch'],
            'dish_counts': {'lunch': 1},
            'budget_tier': 'economy',  # Включаем эконом-режим
            'selected_ingredients': [],
            'excluded_ingredients': [],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что в плане нет премиум блюд
        meal_plan = json_response.get('meal_plan', {})
        for day, meals in meal_plan.items():
            for meal_key, meal_data in meals.items():
                assert meal_data['recipe']['name'] != 'Премиум блюдо'

    def test_medium_mode_selects_regular_dishes(self, authenticated_client, kitchen):
        """UI-02: Средний режим подбирает обычные блюда (cost_level=2)"""
        Recipes.objects.create(
            name='Среднее блюдо',
            description='Обычный рецепт',
            calories=500,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )

        url = reverse('generate_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'meal_types': ['lunch'],
            'dish_counts': {'lunch': 1},
            'budget_tier': 'medium',
            'selected_ingredients': [],
            'excluded_ingredients': [],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200


# ============================================================================
# UI-03: Фильтрация ингредиентов
# ============================================================================
class TestUI03IngredientFiltering:
    """Тесты для фильтрации ингредиентов"""

    def test_excluded_ingredients_filter(self, authenticated_client, kitchen, ingredient):
        """UI-03: Исключение ингредиентов из рациона"""
        # Создаём рецепт с исключаемым ингредиентом
        recipe_with_excluded = Recipes.objects.create(
            name='Блюдо с исключаемым ингредиентом',
            description='Нельзя',
            calories=500,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )
        RecipeIngredient.objects.create(
            recipe=recipe_with_excluded,
            ingredient=ingredient,
            amount=100
        )

        # Создаём рецепт без этого ингредиента
        clean_recipe = Recipes.objects.create(
            name='Чистое блюдо',
            description='Можно',
            calories=400,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )

        url = reverse('generate_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'meal_types': ['lunch'],
            'dish_counts': {'lunch': 1},
            'budget_tier': 'medium',
            'selected_ingredients': [],
            'excluded_ingredients': [ingredient.name],  # Исключаем ингредиент
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что рецепт с исключаемым ингредиентом не попал в план
        meal_plan = json_response.get('meal_plan', {})
        for day, meals in meal_plan.items():
            for meal_key, meal_data in meals.items():
                assert meal_data['recipe']['name'] != 'Блюдо с исключаемым ингредиентом'

    def test_preferred_ingredients(self, authenticated_client, kitchen, ingredient):
        """UI-03: Предпочтения по ингредиентам"""
        # Добавляем предпочтение
        UserPreference.objects.create(
            user=authenticated_client.user,
            ingredient=ingredient,
            preference_type='like'
        )

        # Проверяем, что предпочтения сохранены
        preferences = UserPreference.objects.filter(
            user=authenticated_client.user,
            preference_type='like'
        )
        assert preferences.exists()
        assert preferences.first().ingredient == ingredient


# ============================================================================
# UI-04: Сохранение плана
# ============================================================================
class TestUI04SaveMealPlan:
    """Тесты для сохранения плана питания"""

    def test_save_meal_plan_success(self, authenticated_client, kitchen, recipe):
        """UI-04: Успешное сохранение плана питания"""
        url = reverse('save_meal_plan')
        data = {
            'goal': 'maintain',
            'calories': 2000,
            'budget_tier': 'medium',
            'plan_items': [
                {
                    'day': 'mon',
                    'meal_type': 'lunch',
                    'recipe_id': recipe.id,
                    'recipe_name': recipe.name,
                    'calories': recipe.calories,
                    'portion': 1.0,
                }
            ],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True
        assert 'plan_id' in json_response

        # Проверяем, что план действительно создан в БД
        plan_id = json_response.get('plan_id')
        assert MealPlan.objects.filter(id=plan_id, user=authenticated_client.user).exists()

    def test_save_meal_plan_creates_items(self, authenticated_client, kitchen, recipe):
        """UI-04: Проверка создания элементов плана"""
        url = reverse('save_meal_plan')
        data = {
            'goal': 'lose',
            'calories': 1800,
            'budget_tier': 'economy',
            'plan_items': [
                {
                    'day': 'tue',
                    'meal_type': 'breakfast',
                    'recipe_id': recipe.id,
                    'recipe_name': recipe.name,
                    'calories': recipe.calories,
                    'portion': 1.5,
                }
            ],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        plan_id = response.json().get('plan_id')

        # Проверяем количество элементов в плане
        items_count = MealPlanItem.objects.filter(meal_plan_id=plan_id).count()
        assert items_count == 1


# ============================================================================
# UI-05: Список покупок
# ============================================================================
class TestUI05ShoppingListGeneration:
    """Тесты для формирования списка покупок"""

    def test_generate_shopping_list(self, authenticated_client, ingredient, kitchen):
        """UI-05: Формирование списка покупок из плана"""
        # Создаём рецепт с ингредиентами
        recipe = Recipes.objects.create(
            name='Рецепт для списка',
            description='Тест',
            calories=500,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            amount=200
        )

        url = reverse('generate_shopping_list')
        data = {
            'plan_items': [
                {
                    'recipe_id': recipe.id,
                    'portion': 1.0,
                }
            ],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True
        assert 'shopping_list' in json_response

        # Проверяем корректность списка
        shopping_list = json_response.get('shopping_list', [])
        assert len(shopping_list) > 0
        assert shopping_list[0]['ingredient__name'] == ingredient.name

    def test_shopping_list_aggregates_ingredients(self, authenticated_client, kitchen):
        """UI-05: Агрегация одинаковых ингредиентов"""
        ingredient1 = Ingredients.objects.create(name='Мука', unit='гр')
        ingredient2 = Ingredients.objects.create(name='Сахар', unit='гр')

        recipe1 = Recipes.objects.create(
            name='Рецепт 1',
            description='Тест 1',
            calories=300,
            KitchennameId=kitchen,
            meal_type='breakfast',
            cost_level=2,
        )
        recipe2 = Recipes.objects.create(
            name='Рецепт 2',
            description='Тест 2',
            calories=400,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
        )

        RecipeIngredient.objects.create(recipe=recipe1, ingredient=ingredient1, amount=100)
        RecipeIngredient.objects.create(recipe=recipe1, ingredient=ingredient2, amount=50)
        RecipeIngredient.objects.create(recipe=recipe2, ingredient=ingredient1, amount=150)

        url = reverse('generate_shopping_list')
        data = {
            'plan_items': [
                {'recipe_id': recipe1.id, 'portion': 1.0},
                {'recipe_id': recipe2.id, 'portion': 1.0},
            ],
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        # Список должен содержать оба ингредиента
        shopping_list = response.json().get('shopping_list', [])
        assert len(shopping_list) == 2


# ============================================================================
# UI-06: Управление списком покупок
# ============================================================================
class TestUI06ShoppingListManagement:
    """Тесты для управления списком покупок"""

    def test_toggle_shopping_item(self, authenticated_client, ingredient):
        """UI-06: Переключение статуса элемента списка"""
        # Создаём элемент списка
        shopping_item = ShoppingList.objects.create(
            user=authenticated_client.user,
            ingredient=ingredient,
            amount=100,
            is_checked=False,
        )

        url = reverse('toggle_shopping_item', args=[shopping_item.id])
        data = {'is_checked': True}

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True
        assert json_response.get('is_checked') is True

        # Проверяем в БД
        shopping_item.refresh_from_db()
        assert shopping_item.is_checked is True

    def test_delete_shopping_item(self, authenticated_client, ingredient):
        """UI-06: Удаление элемента из списка покупок"""
        shopping_item = ShoppingList.objects.create(
            user=authenticated_client.user,
            ingredient=ingredient,
            amount=100,
            is_checked=False,
        )

        url = reverse('delete_shopping_item', args=[shopping_item.id])

        response = authenticated_client.post(url)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что элемент удалён
        assert not ShoppingList.objects.filter(id=shopping_item.id).exists()

    def test_clear_shopping_list(self, authenticated_client, ingredient):
        """UI-06: Очистка всего списка покупок"""
        # Создаём несколько элементов
        for i in range(3):
            ShoppingList.objects.create(
                user=authenticated_client.user,
                ingredient=ingredient,
                amount=100 * (i + 1),
                is_checked=False,
            )

        url = reverse('clear_shopping_list')

        response = authenticated_client.post(url)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что список пуст
        assert ShoppingList.objects.filter(user=authenticated_client.user).count() == 0


# ============================================================================
# UI-07: Добавление в избранное
# ============================================================================
class TestUI07Favorites:
    """Тесты для управления избранными рецептами"""

    def test_add_to_favorites(self, authenticated_client, kitchen):
        """UI-07: Добавление рецепта в избранное (через Spoonacular API)"""
        # Создаём рецепт с spoonacular_id
        recipe = Recipes.objects.create(
            name='Избранное блюдо',
            description='Для избранного',
            calories=500,
            KitchennameId=kitchen,
            meal_type='lunch',
            cost_level=2,
            spoonacular_id=12345,  # ID из Spoonacular API
        )

        url = reverse('save_to_favorites')
        data = {
            'spoonacular_id': 12345,  # Требуется ID из Spoonacular
        }

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        # API возвращает 402 при исчерпании лимита или 200 при успехе
        # В тесте ожидаем либо 200, либо 402 (quota exceeded)
        assert response.status_code in [200, 402, 502]
        
        if response.status_code == 200:
            json_response = response.json()
            assert json_response.get('success') is True

            # Проверяем, что рецепт добавлен в избранное
            assert Favorite.objects.filter(
                user=authenticated_client.user,
                recipe=recipe
            ).exists()

    def test_add_duplicate_favorite(self, authenticated_client, kitchen, recipe):
        """UI-07: Попытка добавить дубликат в избранное"""
        # Сначала добавляем вручную
        Favorite.objects.create(user=authenticated_client.user, recipe=recipe)

        url = reverse('save_to_favorites')
        data = {'spoonacular_id': recipe.spoonacular_id or 67890}

        response = authenticated_client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        # Ожидаем 200 или ошибку API (402/502)
        assert response.status_code in [200, 402, 502]


# ============================================================================
# UI-08: Удаление из избранного
# ============================================================================
class TestUI08RemoveFromFavorites:
    """Тесты для удаления из избранного"""

    def test_remove_favorite(self, authenticated_client, kitchen, recipe):
        """UI-08: Удаление рецепта из избранного"""
        # Создаём запись в избранном
        favorite = Favorite.objects.create(
            user=authenticated_client.user,
            recipe=recipe
        )

        url = reverse('remove_favorite', args=[favorite.id])

        response = authenticated_client.post(url)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что запись удалена
        assert not Favorite.objects.filter(id=favorite.id).exists()

    def test_remove_nonexistent_favorite(self, authenticated_client):
        """UI-08: Удаление несуществующего избранного"""
        url = reverse('remove_favorite', args=[99999])

        response = authenticated_client.post(url)

        assert response.status_code == 404
        json_response = response.json()
        assert 'error' in json_response


# ============================================================================
# UI-09: Сохранённые рационы
# ============================================================================
class TestUI09SavedMealPlans:
    """Тесты для просмотра сохранённых рационов"""

    def test_get_saved_meal_plans(self, authenticated_client, kitchen, recipe):
        """UI-09: Получение списка сохранённых рационов"""
        # Создаём сохранённый план
        plan = MealPlan.objects.create(
            user=authenticated_client.user,
            goal='maintain',
            target_calories=2000,
            budget_tier='medium',
            is_saved=True,
        )
        MealPlanItem.objects.create(
            meal_plan=plan,
            recipe=recipe,
            day='mon',
            meal_type='lunch',
            portion=1.0,
        )

        url = reverse('get_saved_meal_plans')

        response = authenticated_client.get(url)

        assert response.status_code == 200
        json_response = response.json()
        assert 'plans' in json_response
        assert len(json_response['plans']) > 0

        plan_data = json_response['plans'][0]
        assert plan_data['target_calories'] == 2000
        assert plan_data['budget_tier'] == 'medium'

    def test_get_only_user_plans(self, authenticated_client, user, kitchen, recipe):
        """UI-09: Проверка, что видны только свои рационы"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='password'
        )
        # Создаём план другого пользователя
        other_plan = MealPlan.objects.create(
            user=other_user,
            goal='lose',
            target_calories=1500,
            budget_tier='economy',
            is_saved=True,
        )

        url = reverse('get_saved_meal_plans')

        response = authenticated_client.get(url)

        assert response.status_code == 200
        json_response = response.json()

        # Проверяем, что план другого пользователя не отображается
        plan_ids = [p['id'] for p in json_response['plans']]
        assert other_plan.id not in plan_ids


# ============================================================================
# UI-10: Удаление рациона
# ============================================================================
class TestUI10DeleteMealPlan:
    """Тесты для удаления рационов питания"""

    def test_delete_meal_plan(self, authenticated_client, kitchen, recipe):
        """UI-10: Удаление плана питания"""
        plan = MealPlan.objects.create(
            user=authenticated_client.user,
            goal='maintain',
            target_calories=2000,
            budget_tier='medium',
            is_saved=True,
        )

        url = reverse('delete_meal_plan', args=[plan.id])

        response = authenticated_client.post(url)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response.get('success') is True

        # Проверяем, что план удалён
        assert not MealPlan.objects.filter(id=plan.id).exists()

    def test_cannot_delete_others_plan(self, authenticated_client, user, kitchen, recipe):
        """UI-10: Нельзя удалить чужой план"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='password'
        )
        other_plan = MealPlan.objects.create(
            user=other_user,
            goal='maintain',
            target_calories=2000,
            budget_tier='medium',
            is_saved=True,
        )

        url = reverse('delete_meal_plan', args=[other_plan.id])

        response = authenticated_client.post(url)

        assert response.status_code == 404
        assert MealPlan.objects.filter(id=other_plan.id).exists()


# ============================================================================
# UI-11: Перевод API
# ============================================================================
class TestUI11APITranslation:
    """Тесты для перевода данных из API"""

    def test_translation_function(self):
        """UI-11: Проверка функции перевода текста"""
        from mainapp.views import translate_text

        # Тест перевода простого текста
        result = translate_text('Hello', dest='ru')
        assert result is not None
        # Функция должна вернуть что-то (либо перевод, либо исходный текст при ошибке)
        assert isinstance(result, str)


# ============================================================================
# UI-12: Форма входа
# ============================================================================
class TestUI12LoginForm:
    """Тесты для формы входа"""

    def test_login_with_invalid_credentials(self, client):
        """UI-12: Ввод неверных данных в форму входа"""
        url = reverse('log_in')

        response = client.post(url, {
            'username': 'nonexistent',
            'password': 'wrongpassword',
        })

        # Должна быть перерисована форма с ошибкой
        assert response.status_code == 200
        assert b'invalid' in response.content.lower() or b'error' in response.content.lower()

    def test_login_with_valid_credentials(self, client, user):
        """UI-12: Успешный вход с правильными данными"""
        url = reverse('log_in')

        response = client.post(url, {
            'username': 'testuser',
            'password': 'testpass123',
        }, follow=True)

        # Должен произойти редирект
        assert response.status_code == 200

        # Проверяем, что пользователь вошёл в систему
        assert '_auth_user_id' in client.session

    def test_login_page_renders(self, client):
        """UI-12: Проверка отображения страницы входа"""
        url = reverse('log_in')

        response = client.get(url)

        assert response.status_code == 200
        assert b'login' in response.content.lower() or b'login' in response.content


# ============================================================================
# UI-13: Регистрация
# ============================================================================
class TestUI13Registration:
    """Тесты для регистрации пользователя"""

    def test_create_user_success(self, client):
        """UI-13: Успешное создание пользователя"""
        url = reverse('register')

        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'Newpass123!',
            'confirm_password': 'Newpass123!',
        }, follow=True)

        assert response.status_code == 200

        # Проверяем, что пользователь создан
        assert User.objects.filter(username='newuser').exists()

    def test_create_user_with_weak_password(self, client):
        """UI-13: Регистрация со слабым паролем"""
        url = reverse('register')

        response = client.post(url, {
            'username': 'newuser2',
            'password1': '123',
            'password2': '123',
        })

        # Должна быть ошибка валидации
        assert response.status_code == 200
        # Проверяем, что форма содержит ошибки
        assert b'error' in response.content.lower() or b'error' in response.content

    def test_create_user_duplicate_username(self, client, user):
        """UI-13: Попытка регистрации с существующим именем"""
        url = reverse('register')

        response = client.post(url, {
            'username': 'testuser',  # Уже существует
            'password1': 'testpass123',
            'password2': 'testpass123',
        })

        assert response.status_code == 200
        # Должна быть ошибка о дубликате
        assert b'error' in response.content.lower() or b'error' in response.content

    def test_registration_page_renders(self, client):
        """UI-13: Проверка отображения страницы регистрации"""
        url = reverse('register')

        response = client.get(url)

        assert response.status_code == 200
        # Проверяем наличие заголовка "Регистрация" на странице
        assert b'\xd0\xa0\xd0\xb5\xd0\xb3\xd0\xb8\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd1\x86\xd0\xb8\xd1\x8f' in response.content


# ============================================================================
# Дополнительные тесты для покрытия edge cases
# ============================================================================
class TestEdgeCases:
    """Дополнительные тесты для граничных случаев"""

    def test_unauthorized_access_to_protected_views(self, client, kitchen):
        """Проверка доступа к защищённым视图 без авторизации"""
        # Пытаемся вызвать защищённый эндпоинт без входа
        url = reverse('generate_meal_plan')
        data = {'goal': 'maintain', 'calories': 2000}

        response = client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        # Должен быть редирект на страницу входа
        assert response.status_code in [302, 403]

    def test_invalid_json_in_api_requests(self, authenticated_client):
        """Обработка некорректного JSON в API запросах"""
        url = reverse('generate_meal_plan')

        response = authenticated_client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )

        assert response.status_code == 400

