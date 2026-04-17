from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from .models import Recipes, Ingredients, MealPlan, MealPlanItem, ShoppingList, UserPreference, UserSettings
from .forms import UserLoginForm, RegistrationForm
import logging
import requests
import random
from googletrans import Translator

logger = logging.getLogger(__name__)
translator = Translator()


def index(request):
    # Оставляем только избранные рецепты для главной страницы
    featured_recipe_names = [
        'Бефстроганов с грибами Белла',
        'Немецкий гуляш',
        'Борщ с говядиной по-шанхайски',
        'Венгерский суп-гуляш',
        'Румынское рагу из гороха и курицы',
        'Борщ русский',
    ]
    recipes = Recipes.objects.filter(name__in=featured_recipe_names)
    return render(request, 'index.html', {'recipes': recipes})


def log_in(request):
    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = UserLoginForm()

    return render(request, 'login.html', {'form': form})


def register(request):
    if request.method == "POST":
        logger.info('Registration')
        print('Registration')
        form = RegistrationForm(request.POST)
        if form.is_valid():
            logger.info(f"Регистрация нового пользователя: {form.cleaned_data['username']}")
            user = form.save(commit=False)
            # Позже проверить работоспособность без следующий строчки
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('log_in')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def profile(request):
    user = request.user
    return HttpResponse(f"{user.email}  {user.username}")


def recipe_detail(request, recipe_id):
    """Страница с детальным описанием рецепта"""
    recipe = None
    is_api_recipe = False
    api_recipe_data = None
    recipe_ingredients = []

    # Проверяем, является ли recipe_id числом (локальный рецепт)
    if recipe_id.isdigit():
        recipe = Recipes.objects.filter(id=int(recipe_id)).first()
        if recipe:
            # Получаем ингредиенты рецепта
            recipe_ingredients = recipe.recipeingredient_set.all().select_related('ingredient')
    else:
        # Это может быть ID рецепта из Spoonacular API
        try:
            spoonacular_id = int(recipe_id)
            api_url = f'https://api.spoonacular.com/recipes/{spoonacular_id}/information'
            params = {
                'apiKey': settings.SPOONACULAR_API_KEY,
                'includeNutrition': True,
            }

            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            api_recipe_data = response.json()
            is_api_recipe = True

            # Переводим название на русский
            if api_recipe_data.get('title'):
                try:
                    translated = translator.translate(api_recipe_data['title'], dest='ru')
                    api_recipe_data['title_ru'] = translated.text
                except Exception as e:
                    logger.warning(f'Ошибка перевода названия: {e}')
                    api_recipe_data['title_ru'] = api_recipe_data['title']

            # Переводим ингредиенты
            if api_recipe_data.get('extendedIngredients'):
                for ingredient in api_recipe_data['extendedIngredients']:
                    original_name = ingredient.get('name', '')
                    if original_name:
                        try:
                            translated = translator.translate(original_name, dest='ru')
                            ingredient['name_ru'] = translated.text
                        except Exception:
                            ingredient['name_ru'] = original_name

            # Переводим инструкции
            if api_recipe_data.get('analyzedInstructions'):
                for instruction_group in api_recipe_data['analyzedInstructions']:
                    if instruction_group.get('steps'):
                        for step in instruction_group['steps']:
                            step_text = step.get('step', '')
                            if step_text:
                                try:
                                    translated = translator.translate(step_text, dest='ru')
                                    step['step_ru'] = translated.text
                                except Exception:
                                    step['step_ru'] = step_text

        except (ValueError, requests.RequestException) as e:
            logger.error(f'Ошибка получения рецепта из Spoonacular: {e}')
            return render(request, 'recipe_not_found.html', status=404)

    context = {
        'recipe': recipe,
        'is_api_recipe': is_api_recipe,
        'api_recipe_data': api_recipe_data,
        'recipe_ingredients': recipe_ingredients if recipe else [],
    }
    return render(request, 'recipe_detail.html', context)


def compose_dish(request):
    ingridients = Ingredients.objects.all()
    return render(request, 'compose_dish.html', {'ingridients': ingridients})


KITCHEN_MAP = {
    'asian': 'Asian',
    'european': 'European',
    'eastern_european': 'Eastern European',
    'chinese': 'Chinese',
    'french': 'French',
    'greek': 'Greek',
    'japanese': 'Japanese',
    'middle_eastern': 'Middle Eastern',
    'vietnamese': 'Vietnamese',
}


def search_recipes(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    ingredients_raw = request.GET.get('ingredients', '').strip()
    kitchen = request.GET.get('kitchen', '').strip()

    # Переводим ингредиенты с русского на английский для Spoonacular API
    ingredients = ingredients_raw
    if ingredients_raw:
        try:
            # Разбиваем по запятым и переводим каждый ингредимент отдельно
            ingr_list = [i.strip() for i in ingredients_raw.split(',') if i.strip()]
            translated_ingrs = []
            for ingr in ingr_list:
                translated = translator.translate(ingr, src='ru', dest='en')
                translated_ingrs.append(translated.text.strip())
            # Объединяем через + для Spoonacular API (это AND-логика)
            ingredients = '+'.join(translated_ingrs)
            logger.info(f'Перевод ингредиентов: "{ingredients_raw}" -> "{ingredients}"')
        except Exception as e:
            logger.warning(f'Ошибка перевода ингредиентов: {e}')
            # Фоллбэк: используем как есть, но заменяем запятые на +
            ingredients = '+'.join([i.strip() for i in ingredients_raw.split(',') if i.strip()])

    params = {
        'apiKey': settings.SPOONACULAR_API_KEY,
        'number': 12,
        'addRecipeInformation': True,
    }

    if ingredients:
        params['includeIngredients'] = ingredients
    if kitchen:
        api_cuisine = KITCHEN_MAP.get(kitchen, kitchen)
        params['cuisine'] = api_cuisine

    logger.info(
        f'Search params: ingredients="{ingredients}", kitchen="{kitchen}" -> API cuisine="{params.get("cuisine")}"')

    try:
        response = requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Если ничего не найдено по всем ингредиентам, пробуем поиск только по кухне
        if not data.get('results') and ingredients:
            logger.info('Ничего не найдено по ингредиентам, пробуем поиск только по кухне')
            fallback_params = {
                'apiKey': settings.SPOONACULAR_API_KEY,
                'number': 12,
                'addRecipeInformation': True,
            }
            if kitchen:
                fallback_params['cuisine'] = KITCHEN_MAP.get(kitchen, kitchen)

            fallback_response = requests.get(
                'https://api.spoonacular.com/recipes/complexSearch',
                params=fallback_params,
                timeout=10,
            )
            fallback_response.raise_for_status()
            data = fallback_response.json()
            logger.info(f'Расширенный поиск вернул {len(data.get("results", []))} рецептов')

        if data.get('results'):
            for recipe in data['results']:
                if recipe.get('title'):
                    try:
                        translated = translator.translate(recipe['title'], dest='ru')
                        recipe['title_ru'] = translated.text
                    except Exception as e:
                        logger.warning(f'Ошибка перевода для "{recipe["title"]}": {e}')
                        recipe['title_ru'] = recipe['title']

        return JsonResponse(data)
    except requests.exceptions.HTTPError as e:
        if response.status_code == 402:
            logger.error('Spoonacular API: лимит бесплатных запросов исчерпан')
            return JsonResponse({
                'error': 'Лимит бесплатных запросов к API исчерпан. Попробуйте позже.',
                'status': 'quota_exceeded'
            }, status=402)
        logger.error(f'Spoonacular API HTTP error: {e}')
        return JsonResponse({'error': 'Ошибка при запросе к API'}, status=502)
    except requests.RequestException as e:
        logger.error(f'Spoonacular API error: {e}')
        return JsonResponse({'error': 'Ошибка при запросе к API'}, status=502)


def meal_plan(request):
    """Страница составления рациона питания"""
    # Загружаем настройки пользователя по умолчанию
    user_settings = None
    if request.user.is_authenticated:
        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)

    # Загружаем предпочтения ингредиентов
    liked_ingredients = []
    disliked_ingredients = []
    if request.user.is_authenticated:
        liked_ingredients = UserPreference.objects.filter(
            user=request.user, preference_type='like'
        ).select_related('ingredient')
        disliked_ingredients = UserPreference.objects.filter(
            user=request.user, preference_type='dislike'
        ).select_related('ingredient')

    # Загружаем все ингредиенты для тегов
    all_ingredients = Ingredients.objects.all()[:50]

    context = {
        'user_settings': user_settings,
        'liked_ingredients': liked_ingredients,
        'disliked_ingredients': disliked_ingredients,
        'all_ingredients': all_ingredients,
    }
    return render(request, 'meal_plan.html', context)


@require_POST
@login_required(login_url='log_in')
def generate_meal_plan(request):
    """Генерация плана питания на неделю"""
    import json
    import traceback

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error(f'JSON decode error: {request.body}')
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    try:
        goal = data.get('goal', 'maintain')
        target_calories = int(data.get('calories', 2000))
        meal_types = data.get('meal_types', ['breakfast', 'lunch', 'dinner'])
        dish_counts = data.get('dish_counts', {'breakfast': 2, 'lunch': 2, 'dinner': 2, 'snack': 1})
        budget_mode = data.get('budget_mode', False)
        selected_ingredients = data.get('selected_ingredients', [])
        excluded_ingredients = data.get('excluded_ingredients', [])

        logger.info(
            f'Генерация рациона: goal={goal}, calories={target_calories}, budget={budget_mode}, meal_types={meal_types}, dish_counts={dish_counts}')

        # Определяем распределение калорий по приёмам пищи
        calorie_distribution = {
            'breakfast': 0.25,
            'lunch': 0.35,
            'dinner': 0.30,
            'snack': 0.10,
        }

        days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        meal_plan_data = {}

        # Получаем disliked ingredient IDs для исключения
        disliked_ids = []
        if request.user.is_authenticated:
            disliked_ids = list(
                UserPreference.objects.filter(
                    user=request.user, preference_type='dislike'
                ).values_list('ingredient_id', flat=True)
            )

        # Если режим экономии — сортируем рецепты по калорийности (дешевле = меньше калорий/простые продукты)
        # ВАЖНО: Не фильтруем жёстко по goal_suitability — используем приоритизацию
        # чтобы всегда был выбор рецептов для любого типа приёма пищи
        recipes_query = Recipes.objects.all().prefetch_related('recipeingredient_set__ingredient')

        # Исключаем нелюбимые ингредиенты
        if disliked_ids:
            recipes_query = recipes_query.exclude(
                recipeingredient__ingredient_id__in=disliked_ids
            )

        # Исключаем ингредиенты из списка "Не добавлять"
        if excluded_ingredients:
            # Находим ingredient IDs по именам (частичное совпадение)
            excluded_ingr_ids = list(
                Ingredients.objects.filter(
                    name__in=excluded_ingredients
                ).values_list('id', flat=True)
            )
            # Также ищем по частичному совпадению (картошка -> картофель)
            for ingr_name in excluded_ingredients:
                partial_matches = Ingredients.objects.filter(
                    name__icontains=ingr_name
                ).values_list('id', flat=True)
                excluded_ingr_ids.extend(partial_matches)

            if excluded_ingr_ids:
                recipes_query = recipes_query.exclude(
                    recipeingredient__ingredient_id__in=set(excluded_ingr_ids)
                )
                logger.info(f'Исключены рецепты с ингредиентами: {excluded_ingredients}')

        if budget_mode:
            # В эконом режиме — рецепты с меньшей калорийностью (обычно дешевле: крупы, супы, простые блюда)
            recipes_query = recipes_query.order_by('calories')
        else:
            recipes_query = recipes_query.order_by('?')  # случайный порядок

        all_recipes = list(recipes_query)

        # API Spoonacular отключён (лимит бесплатных запросов исчерпан)
        # Рецепты берутся только из локальной базы данных

        # Генерируем план на неделю
        # Сначала выбираем рецепты для каждого типа приёма пищи (на всю неделю)
        weekly_recipes = {}  # {meal_type: [recipe1, recipe2, ...]}

        for meal_type in meal_types:
            count = dish_counts.get(meal_type, 2)
            target_meal_calories = int((target_calories * calorie_distribution.get(meal_type, 0.25)) / count)
            weekly_recipes[meal_type] = []

            for i in range(count):
                recipe = _select_recipe_for_meal(
                    all_recipes=all_recipes,
                    meal_type=meal_type,
                    target_calories=target_meal_calories,
                    budget_mode=budget_mode,
                    selected_ingredients=selected_ingredients,
                    used_recipe_ids=set(r['id'] for r_list in weekly_recipes.values() for r in r_list),
                    goal=goal,
                )

                if recipe:
                    # recipe — это объект Recipes из БД
                    recipe_data = {
                        'id': recipe.id,
                        'name': recipe.name,
                        'calories': recipe.calories,
                        'meal_type': recipe.meal_type,
                        'image': recipe.image.url if recipe.image else '',
                        'description': recipe.description[:200] if recipe.description else '',
                    }
                    weekly_recipes[meal_type].append(recipe_data)

        # Теперь распределяем по дням (чередуем рецепты)
        for day in days:
            day_meals = {}
            day_index = days.index(day)

            for meal_type in meal_types:
                recipes_for_type = weekly_recipes.get(meal_type, [])
                if recipes_for_type:
                    # Чередуем: каждый день берём следующий рецепт из списка
                    recipe = recipes_for_type[day_index % len(recipes_for_type)]
                    recipe_key = f"{meal_type}_{recipe['id']}_{day_index}"
                    day_meals[recipe_key] = {
                        'recipe': recipe,
                        'is_api_recipe': False,
                    }

            meal_plan_data[day] = day_meals

        return JsonResponse({
            'success': True,
            'meal_plan': meal_plan_data,
            'target_calories': target_calories,
        })

    except Exception as e:
        logger.error(f'Ошибка генерации рациона: {e}\n{traceback.format_exc()}')
        return JsonResponse({'error': f'Ошибка при генерации рациона: {str(e)}'}, status=500)


@require_POST
@login_required(login_url='log_in')
def save_meal_plan(request):
    """Сохранение плана питания в базу данных"""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    goal = data.get('goal', 'maintain')
    target_calories = int(data.get('calories', 2000))
    budget_mode = data.get('budget_mode', False)
    plan_items = data.get('plan_items', [])  # [{day, meal_type, recipe_id, recipe_name, calories, image}, ...]

    if not plan_items:
        return JsonResponse({'error': 'Пустой план питания'}, status=400)

    # Создаём план
    meal_plan_obj = MealPlan.objects.create(
        user=request.user,
        goal=goal,
        target_calories=target_calories,
        budget_mode=budget_mode,
        is_saved=True,
    )

    saved_items = []

    for item in plan_items:
        recipe = None
        recipe_id = item.get('recipe_id')

        # Если recipe_id числовой — ищем в БД
        if recipe_id and isinstance(recipe_id, int):
            recipe = Recipes.objects.filter(id=recipe_id).first()

        # Если рецепт из API — создаём запись в БД
        if not recipe and item.get('recipe_name'):
            from .models import Kitchenname
            # Находим или создаём кухню по умолчанию
            default_kitchen, _ = Kitchenname.objects.get_or_create(name='Разное')

            recipe = Recipes.objects.create(
                name=item.get('recipe_name', 'Без названия')[:50],
                description=item.get('description', '')[:500] if item.get('description') else 'Рецепт из API',
                calories=int(item.get('calories', 200)),
                image='',  # URL изображения можно сохранить
                KitchennameId=default_kitchen,
            )

        if recipe:
            meal_item = MealPlanItem.objects.create(
                meal_plan=meal_plan_obj,
                recipe=recipe,
                day=item.get('day', 'mon'),
                meal_type=item.get('meal_type', 'lunch'),
                portion=float(item.get('portion', 1.0)),
            )
            saved_items.append({
                'id': meal_item.id,
                'day': meal_item.get_day_display(),
                'meal_type': meal_item.get_meal_type_display(),
                'recipe': recipe.name,
                'calories': recipe.calories,
            })

    # Сохраняем настройки эконом-режима
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    user_settings.budget_mode = budget_mode
    user_settings.default_goal = goal
    user_settings.default_calories = target_calories
    user_settings.save()

    return JsonResponse({
        'success': True,
        'plan_id': meal_plan_obj.id,
        'saved_items': saved_items,
    })


@login_required(login_url='log_in')
def get_saved_meal_plans(request):
    """Получение сохранённых планов пользователя"""
    plans = MealPlan.objects.filter(user=request.user).prefetch_related('items__recipe').order_by('-created_at')

    plans_data = []
    for plan in plans:
        items = []
        for item in plan.items.all():
            items.append({
                'id': item.id,
                'day': item.get_day_display(),
                'meal_type': item.get_meal_type_display(),
                'recipe_name': item.recipe.name,
                'calories': item.recipe.calories,
                'image': item.recipe.image.url if item.recipe.image else '',
            })
        plans_data.append({
            'id': plan.id,
            'goal': plan.goal,
            'target_calories': plan.target_calories,
            'budget_mode': plan.budget_mode,
            'created_at': plan.created_at.strftime('%d.%m.%Y %H:%M'),
            'items': items,
        })

    return JsonResponse({'plans': plans_data})


@require_POST
@login_required(login_url='log_in')
def generate_shopping_list(request):
    """Формирование списка покупок на основе плана питания"""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    plan_items = data.get('plan_items', [])  # [{recipe_id, portion}, ...]

    if not plan_items:
        return JsonResponse({'error': 'Пустой план питания'}, status=400)

    # Очищаем старый список покупок
    ShoppingList.objects.filter(user=request.user).delete()

    shopping_items = []

    for item in plan_items:
        recipe_id = item.get('recipe_id')
        portion = float(item.get('portion', 1.0))

        if not recipe_id:
            continue

        recipe = Recipes.objects.filter(id=recipe_id).first()
        if not recipe:
            continue

        # Получаем ингредиенты рецепта
        recipe_ingredients = recipe.recipeingredient_set.all().select_related('ingredient')

        for ri in recipe_ingredients:
            amount_needed = ri.amount * portion

            # Проверяем, есть ли уже такой ингредиент в списке
            existing = ShoppingList.objects.filter(
                user=request.user,
                ingredient=ri.ingredient,
            ).first()

            if existing:
                existing.amount += int(amount_needed)
                existing.save()
            else:
                ShoppingList.objects.create(
                    user=request.user,
                    ingredient=ri.ingredient,
                    amount=int(amount_needed),
                    is_checked=False,
                )

            shopping_items.append({
                'ingredient': ri.ingredient.name,
                'amount': int(amount_needed),
                'unit': ri.ingredient.unit or '',
            })

    # Возвращаем актуальный список покупок
    current_shopping_list = list(
        ShoppingList.objects.filter(user=request.user)
        .select_related('ingredient')
        .values('id', 'ingredient__name', 'amount', 'is_checked', 'ingredient__unit')
    )

    return JsonResponse({
        'success': True,
        'shopping_list': current_shopping_list,
    })


@login_required(login_url='log_in')
def get_shopping_list(request):
    """Получение текущего списка покупок"""
    shopping_list = list(
        ShoppingList.objects.filter(user=request.user)
        .select_related('ingredient')
        .values('id', 'ingredient__name', 'amount', 'is_checked', 'ingredient__unit')
    )
    return JsonResponse({'shopping_list': shopping_list})


@require_POST
@login_required(login_url='log_in')
def save_to_favorites(request):
    """Сохранение плана в избранное"""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    recipe_ids = data.get('recipe_ids', [])
    saved_count = 0

    from .models import Favorite

    for recipe_id in recipe_ids:
        recipe = Recipes.objects.filter(id=recipe_id).first()
        if recipe:
            Favorite.objects.get_or_create(user=request.user, recipe=recipe)
            saved_count += 1

    return JsonResponse({'success': True, 'saved_count': saved_count})


# === Вспомогательные функции ===

def _fetch_recipes_from_api(budget_mode=False, selected_ingredients=None, number=20):
    """Получение рецептов из Spoonacular API"""
    if selected_ingredients is None:
        selected_ingredients = []

    params = {
        'apiKey': settings.SPOONACULAR_API_KEY,
        'number': number,
        'addRecipeInformation': True,
        'addRecipeNutrition': True,
        'sort': 'calories' if budget_mode else 'random',
    }

    # В эконом режиме — дешевле (меньше калорий)
    if budget_mode:
        params['maxCalories'] = 400

    # Выбранные ингредиенты
    if selected_ingredients:
        try:
            translated = translator.translate(', '.join(selected_ingredients), src='ru', dest='en')
            params['includeIngredients'] = translated.text
        except Exception as e:
            logger.warning(f'Ошибка перевода ингредиентов для API: {e}')

    try:
        response = requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        recipes = []
        for r in data.get('results', []):
            # Переводим название на русский
            title_ru = r.get('title', '')
            try:
                translated = translator.translate(title_ru, dest='ru')
                title_ru = translated.text
            except Exception:
                pass

            # Получаем калории из nutrition
            calories = 200
            nutrients = r.get('nutrition', {}).get('nutrients', [])
            for n in nutrients:
                if n.get('name') == 'Calories':
                    calories = int(n.get('amount', 200))
                    break

            recipes.append({
                'id': r.get('id'),
                'name': title_ru,
                'calories': calories,
                'image': r.get('image', ''),
                'description': r.get('summary', '')[:500] if r.get('summary') else '',
            })

        return recipes

    except Exception as e:
        logger.error(f'Ошибка Spoonacular API при генерации рациона: {e}')
        return []


def _select_recipe_for_meal(all_recipes, meal_type, target_calories, budget_mode,
                            selected_ingredients, used_recipe_ids, goal='maintain'):
    """Выбор рецепта для приёма пищи.

    Логика выбора по цели:
    - lose: только рецепты с goal_suitability='lose' или 'any'
    - maintain: только рецепты с goal_suitability='maintain' или 'any'
    - gain: только рецепты с goal_suitability='gain' или 'any'
    - Fallback: если не нашлось — берём ЛЮБОЙ рецепт этого типа
    """

    used_recipe_ids = used_recipe_ids or set()

    # Этап 1: Отбираем рецепты с нужным meal_type И подходящей целью
    goal_matched = []  # goal_suitability == goal
    any_matched = []  # goal_suitability == 'any'
    all_by_type = []  # все рецепты этого типа (fallback)

    for recipe in all_recipes:
        recipe_id = recipe.get('id') if isinstance(recipe, dict) else recipe.id
        if recipe_id in used_recipe_ids:
            continue

        recipe_meal_type = recipe.get('meal_type') if isinstance(recipe, dict) else getattr(recipe, 'meal_type', None)
        if recipe_meal_type != meal_type:
            continue

        all_by_type.append(recipe)

        recipe_goal = recipe.get('goal_suitability') if isinstance(recipe, dict) else getattr(recipe,
                                                                                              'goal_suitability', 'any')
        if recipe_goal == goal:
            goal_matched.append(recipe)
        elif recipe_goal == 'any':
            any_matched.append(recipe)

    # Приоритет: рецепты для выбранной цели > универсальные > все остальные
    if goal_matched:
        candidates = goal_matched
    elif any_matched:
        candidates = any_matched
    else:
        # Fallback — берём ВСЕ рецепты этого типа
        if not all_by_type:
            logger.warning(f'НЕ НАЙДЕНО рецептов для meal_type={meal_type} (цель: {goal})!')
            return None
        candidates = all_by_type

    # Этап 2: Дополнительная фильтрация по калориям в зависимости от цели
    if goal == 'lose':
        # Похудение — низкокалорийные блюда
        candidates.sort(key=lambda r: r.get('calories', 500) if isinstance(r, dict) else r.calories)
        max_cal = int(target_calories * 1.3)
        filtered = [r for r in candidates if (r.get('calories', 500) if isinstance(r, dict) else r.calories) <= max_cal]
        if filtered:
            candidates = filtered

    elif goal == 'gain':
        # Набор массы — высококалорийные блюда
        candidates.sort(key=lambda r: -(r.get('calories', 500) if isinstance(r, dict) else r.calories))
        min_cal = int(target_calories * 0.7)
        filtered = [r for r in candidates if (r.get('calories', 500) if isinstance(r, dict) else r.calories) >= min_cal]
        if filtered:
            candidates = filtered

    # Для maintain — без дополнительной фильтрации по калориям

    # Этап 3: Эконом-режим — самые дешёвые (меньше калорий = дешевле)
    if budget_mode:
        candidates.sort(key=lambda r: r.get('calories', 500) if isinstance(r, dict) else r.calories)
        candidates = candidates[:min(3, len(candidates))]

    if not candidates:
        return None

    chosen = random.choice(candidates)
    chosen_name = chosen.get('name') if isinstance(chosen, dict) else chosen.name
    chosen_goal = chosen.get('goal_suitability') if isinstance(chosen, dict) else getattr(chosen, 'goal_suitability',
                                                                                          '?')
    logger.info(f'Выбран рецепт для {meal_type}: {chosen_name} ({chosen_goal} ккал, цель: {goal})')
    return chosen
