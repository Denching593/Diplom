from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from .models import Recipes, Ingredients, MealPlan, MealPlanItem, ShoppingList, UserPreference, UserSettings
from .forms import UserLoginForm, RegistrationForm
from functools import lru_cache
import logging
import requests
import random
import json
import time
from googletrans import Translator

logger = logging.getLogger(__name__)
translator = Translator()


def translate_text(text, dest='ru', src=None, max_retries=3):
    """
    Надёжный перевод текста с повторными попытками.
    
    Args:
        text: Текст для перевода
        dest: Язык назначения (по умолчанию 'ru')
        src: Исходный язык (None = автоопределение)
        max_retries: Максимальное количество попыток
    
    Returns:
        Переведённый текст или оригинал при ошибке
    """
    if not text or not isinstance(text, str):
        return text
    
    text = text.strip()
    if not text:
        return text
    
    for attempt in range(max_retries):
        try:
            kwargs = {'dest': dest}
            if src:
                kwargs['src'] = src
            
            result = translator.translate(text, **kwargs)
            if result and hasattr(result, 'text') and result.text:
                return result.text
        except Exception as e:
            logger.debug(f'Попытка {attempt + 1} перевода не удалась: {e}')
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Экспоненциальная задержка
    
    # Возвращаем оригинал при всех неудачах
    logger.warning(f'Не удалось перевести текст после {max_retries} попыток: {text[:50]}...')
    return text


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
            next_url = request.POST.get('next') or request.GET.get('next') or 'index'
            return redirect(next_url)
    else:
        form = UserLoginForm()

    next_url = request.GET.get('next', '')
    return render(request, 'login.html', {'form': form, 'next': next_url})


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


@login_required(login_url='log_in')
def profile(request):
    """Профиль пользователя: избранные блюда, рационы, список покупок"""
    user = request.user

    # Избранные блюда
    from .models import Favorite
    favorites = Favorite.objects.filter(user=user).select_related('recipe')[:20]

    # Сохранённые рационы питания
    meal_plans = MealPlan.objects.filter(user=user, is_saved=True).prefetch_related('items__recipe').order_by('-created_at')[:5]

    # Список покупок
    shopping_list = ShoppingList.objects.filter(user=user).select_related('ingredient')

    # Настройки пользователя
    user_settings, _ = UserSettings.objects.get_or_create(user=user)

    context = {
        'user': user,
        'favorites': favorites,
        'meal_plans': meal_plans,
        'shopping_list': shopping_list,
        'user_settings': user_settings,
    }
    return render(request, 'profile.html', context)


def recipe_detail(request, recipe_id):
    """Страница с детальным описанием рецепта"""
    recipe = None
    is_api_recipe = False
    api_recipe_data = None
    recipe_ingredients = []

    # Сначала пробуем найти рецепт в локальной БД (если recipe_id число)
    if recipe_id.isdigit():
        recipe = Recipes.objects.filter(id=int(recipe_id)).first()
        if recipe:
            # Получаем ингредиенты рецепта из локальной БД
            recipe_ingredients = recipe.recipeingredient_set.all().select_related('ingredient')
            context = {
                'recipe': recipe,
                'is_api_recipe': False,
                'api_recipe_data': None,
                'recipe_ingredients': recipe_ingredients,
            }
            return render(request, 'recipe_detail.html', context)

    # Если локальный рецепт не найден или recipe_id не число — пробуем Spoonacular API
    try:
        spoonacular_id = int(recipe_id)
        api_url = f'https://api.spoonacular.com/recipes/{spoonacular_id}/information'
        params = {
            'apiKey': settings.SPOONACULAR_API_KEY,
            'includeNutrition': True,
        }

        response = requests.get(api_url, params=params, timeout=10)

        if response.status_code == 404:
            # Рецепт действительно не найден
            logger.warning(f'Рецепт с ID {spoonacular_id} не найден в Spoonacular API')
            return render(request, 'recipe_not_found.html', status=404)

        response.raise_for_status()
        api_recipe_data = response.json()
        is_api_recipe = True

        # Переводим название на русский
        if api_recipe_data.get('title'):
            api_recipe_data['title_ru'] = translate_text(api_recipe_data['title'], dest='ru')

        # Переводим ингредиенты
        if api_recipe_data.get('extendedIngredients'):
            for ingredient in api_recipe_data['extendedIngredients']:
                original_name = ingredient.get('name', '')
                if original_name:
                    ingredient['name_ru'] = translate_text(original_name, dest='ru')

        # Переводим инструкции
        if api_recipe_data.get('analyzedInstructions'):
            for instruction_group in api_recipe_data['analyzedInstructions']:
                if instruction_group.get('steps'):
                    for step in instruction_group['steps']:
                        step_text = step.get('step', '')
                        if step_text:
                            step['step_ru'] = translate_text(step_text, dest='ru')

    except ValueError:
        # recipe_id не является числом
        logger.warning(f'Неверный формат recipe_id: {recipe_id}')
        return render(request, 'recipe_not_found.html', status=404)
    except requests.RequestException as e:
        logger.error(f'Ошибка получения рецепта из Spoonacular: {e}')
        return render(request, 'recipe_not_found.html', status=404)

    context = {
        'recipe': None,
        'is_api_recipe': is_api_recipe,
        'api_recipe_data': api_recipe_data,
        'recipe_ingredients': [],
    }
    return render(request, 'recipe_detail.html', context)


@lru_cache(maxsize=128)
def _fetch_recipe_details_from_api(recipe_id):
    """Кэшированное получение деталей рецепта из Spoonacular API.

    Возвращает кортеж: (api_recipe_data, recipe_steps) или (None, None) при ошибке.
    Кэширует шаги приготовления и ингредиенты для одного рецепта.
    """
    try:
        api_url = f'https://api.spoonacular.com/recipes/{recipe_id}/information'
        params = {
            'apiKey': settings.SPOONACULAR_API_KEY,
            'includeNutrition': True,
        }

        response = requests.get(api_url, params=params, timeout=10)

        if response.status_code == 404:
            logger.warning(f'Рецепт с ID {recipe_id} не найден в Spoonacular API')
            return None, None

        response.raise_for_status()
        api_recipe_data = response.json()

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

        # Получаем шаги из инструкций
        recipe_steps = []
        if api_recipe_data.get('analyzedInstructions'):
            for instruction_group in api_recipe_data['analyzedInstructions']:
                if instruction_group.get('steps'):
                    for step in instruction_group['steps']:
                        step_text = step.get('step', '')
                        if step_text:
                            # Переводим текст шага
                            try:
                                translated = translator.translate(step_text, dest='ru')
                                translated_text = translated.text
                            except Exception:
                                translated_text = step_text

                            # Переводим ингредиенты шага
                            step_ingredients = []
                            for ing in step.get('ingredients', []):
                                ing_name = ing.get('name') or ''
                                if ing_name:
                                    try:
                                        translated_ing = translator.translate(ing_name, dest='ru')
                                        step_ingredients.append({
                                            'name': ing_name,
                                            'name_ru': translated_ing.text
                                        })
                                    except Exception:
                                        step_ingredients.append({
                                            'name': ing_name,
                                            'name_ru': ing_name
                                        })

                            # Получаем время шага
                            step_length = step.get('length', None)

                            recipe_steps.append({
                                'number': step.get('number', len(recipe_steps) + 1),
                                'text': translated_text,
                                'ingredients': step_ingredients,
                                'length': step_length
                            })

        return api_recipe_data, recipe_steps

    except requests.RequestException as e:
        logger.error(f'Ошибка получения рецепта {recipe_id} из Spoonacular: {e}')
        return None, None


def recipe_cooking(request, recipe_id):
    """Страница приготовления рецепта с таймером и чекбоксами"""
    recipe = None
    is_api_recipe = False
    is_local_recipe = False
    api_recipe_data = None
    recipe_steps = []

    # Сначала пробуем найти рецепт в локальной БД (если recipe_id число)
    if recipe_id.isdigit():
        recipe = Recipes.objects.filter(id=int(recipe_id)).first()
        if recipe:
            is_local_recipe = True
            # Шаги подгружаются из Spoonacular API через AJAX на клиенте
            # Серверные шаги используются как фоллбэк
            if recipe.description:
                import re
                sentences = re.split(r'(?<=[.!?])\s+', recipe.description)
                for i, sentence in enumerate(sentences, 1):
                    if sentence.strip():
                        recipe_steps.append({
                            'number': i,
                            'text': sentence.strip(),
                            'ingredients': []
                        })
            context = {
                'recipe': recipe,
                'is_api_recipe': False,
                'is_local_recipe': True,
                'api_recipe_data': None,
                'recipe_steps': recipe_steps,
                'recipe_id': recipe_id,
            }
            return render(request, 'recipe_cooking.html', context)

    # Если локальный рецепт не найден или recipe_id не число — пробуем Spoonacular API
    try:
        spoonacular_id = int(recipe_id)
        api_recipe_data, recipe_steps = _fetch_recipe_details_from_api(spoonacular_id)

        if api_recipe_data is None:
            return render(request, 'recipe_not_found.html', status=404)

        is_api_recipe = True

    except ValueError:
        logger.warning(f'Неверный формат recipe_id: {recipe_id}')
        return render(request, 'recipe_not_found.html', status=404)

    context = {
        'recipe': recipe,
        'is_api_recipe': is_api_recipe,
        'is_local_recipe': False,
        'api_recipe_data': api_recipe_data,
        'recipe_steps': recipe_steps,
        'recipe_id': recipe_id,
    }
    return render(request, 'recipe_cooking.html', context)


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


@login_required(login_url='log_in')
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
        budget_tier = data.get('budget_tier', 'medium')
        selected_ingredients = data.get('selected_ingredients', [])
        excluded_ingredients = data.get('excluded_ingredients', [])

        logger.info(
            f'Генерация рациона: goal={goal}, calories={target_calories}, budget={budget_tier}, meal_types={meal_types}, dish_counts={dish_counts}')

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

        # Фильтруем рецепты по уровню бюджета
        if budget_tier == 'economy':
            # Эконом — только дешёвые рецепты (cost_level=1)
            recipes_query = recipes_query.filter(cost_level=1)
        elif budget_tier == 'premium':
            # Премиум — только дорогие рецепты (cost_level=3)
            recipes_query = recipes_query.filter(cost_level=3)
        else:
            # Средний — средние рецепты (cost_level=2), но можно и 1 или 3
            recipes_query = recipes_query.filter(cost_level=2)

        # Случайный порядок для разнообразия
        recipes_query = recipes_query.order_by('?')

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
                    budget_tier=budget_tier,
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
    budget_tier = data.get('budget_tier', 'medium')
    plan_items = data.get('plan_items', [])  # [{day, meal_type, recipe_id, recipe_name, calories, image}, ...]

    if not plan_items:
        return JsonResponse({'error': 'Пустой план питания'}, status=400)

    # Создаём план
    meal_plan_obj = MealPlan.objects.create(
        user=request.user,
        goal=goal,
        target_calories=target_calories,
        budget_tier=budget_tier,
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

    # Сохраняем настройки бюджета
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    user_settings.budget_tier = budget_tier
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
            'budget_tier': plan.budget_tier,
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
    """Сохранение рецепта в избранное (только из Spoonacular API)"""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    spoonacular_id = data.get('spoonacular_id')

    if not spoonacular_id:
        return JsonResponse({'error': 'В избранное можно добавлять только рецепты из Spoonacular API'}, status=400)

    from .models import Favorite, Kitchenname

    # Проверяем, существует ли рецепт с таким spoonacular_id в локальной БД
    recipe = Recipes.objects.filter(spoonacular_id=spoonacular_id).first()

    if not recipe:
        # Рецепта нет в БД — получаем данные из Spoonacular API и создаём запись
        try:
            api_url = f'https://api.spoonacular.com/recipes/{spoonacular_id}/information'
            params = {
                'apiKey': settings.SPOONACULAR_API_KEY,
                'includeNutrition': True,
            }
            response = requests.get(api_url, params=params, timeout=10)

            if response.status_code == 404:
                return JsonResponse({'error': 'Рецепт не найден в Spoonacular API'}, status=404)

            response.raise_for_status()
            api_data = response.json()

            # Получаем калории
            calories = 0
            if api_data.get('nutrition', {}).get('nutrients'):
                for n in api_data['nutrition']['nutrients']:
                    if n.get('name') == 'Calories':
                        calories = int(n.get('amount', 0))
                        break

            # Переводим название
            title = api_data.get('title', 'Без названия')
            try:
                translated = translator.translate(title, dest='ru')
                title_ru = translated.text[:50]
            except Exception:
                title_ru = title[:50]

            # Находим или создаём кухню
            cuisines = api_data.get('cuisines', [])
            kitchen_name = cuisines[0] if cuisines else 'Разное'
            try:
                translated_kitchen = translator.translate(kitchen_name, dest='ru')
                kitchen_name = translated_kitchen.text[:50]
            except Exception:
                pass
            default_kitchen, _ = Kitchenname.objects.get_or_create(name=kitchen_name[:50])

            # Создаём рецепт в локальной БД
            recipe = Recipes.objects.create(
                name=title_ru,
                description=api_data.get('summary', '')[:500] if api_data.get('summary') else '',
                calories=calories,
                image='',
                KitchennameId=default_kitchen,
                spoonacular_id=spoonacular_id,
            )
            logger.info(f'Создан рецепт из Spoonacular API: {recipe.name} (spoonacular_id={spoonacular_id})')

        except requests.RequestException as e:
            logger.error(f'Ошибка Spoonacular API при добавлении в избранное: {e}')
            return JsonResponse({'error': 'Ошибка при проверке рецепта в Spoonacular API'}, status=502)

    # Проверяем, не добавлен ли уже в избранное
    favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)

    if not created:
        return JsonResponse({'success': True, 'message': 'Рецепт уже в избранном', 'already_exists': True})

    return JsonResponse({'success': True, 'recipe_name': recipe.name})


@require_GET
def fetch_recipe_from_api(request, recipe_id):
    """AJAX-эндпоинт: получение детальной информации о рецепте из Spoonacular API"""
    recipe = None
    spoonacular_id = None

    # Пробуем найти рецепт в локальной БД
    if recipe_id.isdigit():
        recipe = Recipes.objects.filter(id=int(recipe_id)).first()

    try:
        if recipe:
            # Локальный рецепт — ищем в Spoonacular по названию
            try:
                translated_name = translator.translate(recipe.name, src='ru', dest='en').text
            except Exception:
                translated_name = recipe.name

            search_url = 'https://api.spoonacular.com/recipes/complexSearch'
            search_params = {
                'apiKey': settings.SPOONACULAR_API_KEY,
                'query': translated_name,
                'number': 1,
                'addRecipeInformation': True,
            }

            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data.get('results'):
                spoonacular_id = search_data['results'][0]['id']
            else:
                return JsonResponse({'error': 'Рецепт не найден в Spoonacular API'}, status=404)
        else:
            spoonacular_id = int(recipe_id)

        # Получаем полную информацию о рецепте из Spoonacular
        api_url = f'https://api.spoonacular.com/recipes/{spoonacular_id}/information'
        params = {
            'apiKey': settings.SPOONACULAR_API_KEY,
            'includeNutrition': True,
        }

        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()

        # Формируем результат
        result = {
            'id': api_data.get('id'),
            'title': api_data.get('title', ''),
            'image': api_data.get('image', ''),
            'readyInMinutes': api_data.get('readyInMinutes'),
            'servings': api_data.get('servings'),
            'cuisines': api_data.get('cuisines', []),
            'veryHealthy': api_data.get('veryHealthy', False),
            'vegetarian': api_data.get('vegetarian', False),
            'vegan': api_data.get('vegan', False),
            'glutenFree': api_data.get('glutenFree', False),
            'dairyFree': api_data.get('dairyFree', False),
            'cheap': api_data.get('cheap', False),
            'summary': '',
            'ingredients': [],
            'instructions': [],
            'nutrients': [],
        }

        # Переводим название
        if result['title']:
            try:
                translated = translator.translate(result['title'], dest='ru')
                result['title_ru'] = translated.text
            except Exception:
                result['title_ru'] = result['title']

        # Переводим summary
        if api_data.get('summary'):
            try:
                translated = translator.translate(api_data['summary'], dest='ru')
                result['summary'] = translated.text
            except Exception:
                result['summary'] = api_data['summary']

        # Переводим ингредиенты
        if api_data.get('extendedIngredients'):
            for ing in api_data['extendedIngredients']:
                name = ing.get('name', '')
                name_ru = name
                if name:
                    try:
                        translated = translator.translate(name, dest='ru')
                        name_ru = translated.text
                    except Exception:
                        pass

                unit = ing.get('unit', '')
                if not unit and ing.get('measures', {}).get('metric', {}).get('unitShort'):
                    unit = ing['measures']['metric']['unitShort']

                result['ingredients'].append({
                    'name': name,
                    'name_ru': name_ru,
                    'amount': ing.get('amount', 0),
                    'unit': unit,
                })

        # Переводим инструкции
        if api_data.get('analyalyzedInstructions') or api_data.get('analyzedInstructions'):
            instructions_data = api_data.get('analyalyzedInstructions') or api_data.get('analyzedInstructions', [])
            for group in instructions_data:
                if group.get('steps'):
                    for step in group['steps']:
                        step_text = step.get('step', '')
                        step_text_ru = step_text
                        if step_text:
                            try:
                                translated = translator.translate(step_text, dest='ru')
                                step_text_ru = translated.text
                            except Exception:
                                pass

                        step_ingredients = []
                        for ing in step.get('ingredients', []):
                            ing_name = ing.get('name', '')
                            ing_name_ru = ing_name
                            if ing_name:
                                try:
                                    translated = translator.translate(ing_name, dest='ru')
                                    ing_name_ru = translated.text
                                except Exception:
                                    pass
                            step_ingredients.append({'name': ing_name, 'name_ru': ing_name_ru})

                        result['instructions'].append({
                            'number': step.get('number', 1),
                            'text': step_text_ru,
                            'ingredients': step_ingredients,
                            'length': step.get('length'),
                        })

        # Извлекаем питательные вещества
        if api_data.get('nutrition', {}).get('nutrients'):
            for n in api_data['nutrition']['nutrients']:
                if n.get('name') in ['Calories', 'Protein', 'Fat', 'Carbohydrates']:
                    result['nutrients'].append({
                        'name': n['name'],
                        'amount': round(n.get('amount', 0), 1),
                        'unit': n.get('unit', ''),
                    })

        return JsonResponse(result)

    except ValueError:
        return JsonResponse({'error': 'Неверный формат ID'}, status=400)
    except requests.RequestException as e:
        logger.error(f'Ошибка Spoonacular API: {e}')
        return JsonResponse({'error': 'Ошибка при запросе к API'}, status=502)


@require_POST
@login_required(login_url='log_in')
def remove_favorite(request, fav_id):
    """Удаление рецепта из избранного"""
    from .models import Favorite
    fav = Favorite.objects.filter(id=fav_id, user=request.user).first()
    if fav:
        fav.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Не найдено'}, status=404)


@require_POST
@login_required(login_url='log_in')
def delete_meal_plan(request, plan_id):
    """Удаление рациона питания"""
    plan = MealPlan.objects.filter(id=plan_id, user=request.user).first()
    if plan:
        plan.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Не найдено'}, status=404)


@require_POST
@login_required(login_url='log_in')
def toggle_shopping_item(request, item_id):
    """Переключение чекбокса в списке покупок"""
    item = ShoppingList.objects.filter(id=item_id, user=request.user).first()
    if item:
        import json as _json
        try:
            data = _json.loads(request.body)
        except _json.JSONDecodeError:
            data = {}
        item.is_checked = data.get('is_checked', not item.is_checked)
        item.save()
        return JsonResponse({'success': True, 'is_checked': item.is_checked})
    return JsonResponse({'error': 'Не найдено'}, status=404)


@require_POST
@login_required(login_url='log_in')
def delete_shopping_item(request, item_id):
    """Удаление элемента из списка покупок"""
    item = ShoppingList.objects.filter(id=item_id, user=request.user).first()
    if item:
        item.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Не найдено'}, status=404)


@require_POST
@login_required(login_url='log_in')
def clear_shopping_list(request):
    """Очистка всего списка покупок"""
    ShoppingList.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True})


def logout_view(request):
    """Выход из аккаунта"""
    from django.contrib.auth import logout
    logout(request)
    return redirect('index')

# === Вспомогательные функции ===
@lru_cache
def _fetch_recipes_from_api(budget_tier='medium', selected_ingredients=None, number=20):
    """Получение рецептов из Spoonacular API"""
    if selected_ingredients is None:
        selected_ingredients = []

    params = {
        'apiKey': settings.SPOONACULAR_API_KEY,
        'number': number,
        'addRecipeInformation': True,
        'addRecipeNutrition': True,
        'sort': 'calories' if budget_tier == 'economy' else 'random',
    }

    # В эконом режиме — меньше калорий
    if budget_tier == 'economy':
        params['maxCalories'] = 400
    # В премиум режиме — более калорийные блюда
    elif budget_tier == 'premium':
        params['minCalories'] = 500

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


def _select_recipe_for_meal(all_recipes, meal_type, target_calories, budget_tier,
                            selected_ingredients, used_recipe_ids, goal='maintain'):
    """Выбор рецепта для приёма пищи.

    Логика выбора по цели:
    - lose: только рецепты с goal_suitability='lose' или 'any'
    - maintain: только рецепты с goal_suitability='maintain' или 'any'
    - gain: только рецепты с goal_suitability='gain' или 'any'
    - Fallback: если не нашлось — берём ЛЮБОЙ рецепт этого типа, или вообще любой
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
    elif all_by_type:
        # Fallback — берём ВСЕ рецепты этого типа
        candidates = all_by_type
    else:
        # Второй fallback — нет рецептов с таким meal_type, берём ВСЕ доступные
        logger.warning(f'НЕ НАЙДЕНО рецептов для meal_type={meal_type} (цель: {goal}), берём любые доступные')
        for recipe in all_recipes:
            recipe_id = recipe.get('id') if isinstance(recipe, dict) else recipe.id
            if recipe_id in used_recipe_ids:
                continue
            recipe_goal = recipe.get('goal_suitability') if isinstance(recipe, dict) else getattr(recipe, 'goal_suitability', 'any')
            if recipe_goal == goal:
                goal_matched.append(recipe)
            elif recipe_goal == 'any':
                any_matched.append(recipe)

        if goal_matched:
            candidates = goal_matched
        elif any_matched:
            candidates = any_matched
        else:
            # Третий fallback — вообще любые неиспользованные рецепты
            candidates = [r for r in all_recipes if (r.get('id') if isinstance(r, dict) else r.id) not in used_recipe_ids]
            if not candidates:
                logger.warning(f'Совсем нет доступных рецептов для meal_type={meal_type}!')
                return None

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
    # Фильтрация по бюджету уже сделана на уровне запроса к БД (cost_level)

    if not candidates:
        return None

    chosen = random.choice(candidates)
    chosen_name = chosen.get('name') if isinstance(chosen, dict) else chosen.name
    chosen_goal = chosen.get('goal_suitability') if isinstance(chosen, dict) else getattr(chosen, 'goal_suitability',
                                                                                          '?')
    logger.info(f'Выбран рецепт для {meal_type}: {chosen_name} ({chosen_goal} ккал, цель: {goal})')
    return chosen