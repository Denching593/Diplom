from django.core.management.base import BaseCommand
from mainapp.models import Recipes, Kitchenname, Ingredients, RecipeIngredient


class Command(BaseCommand):
    help = 'Add missing meal recipes for breakfast, lunch, dinner, snack with all goals'

    def handle(self, *args, **kwargs):
        # Get or create kitchens
        kitchens_data = [
            ('Европейская', 'Европейская'),
            ('Русская', 'Русская'),
            ('Итальянская', 'Итальянская'),
            ('Средиземноморская', 'Средиземноморская'),
            ('Разное', 'Разное'),
        ]
        kitchens = {}
        for key, name in kitchens_data:
            k, _ = Kitchenname.objects.get_or_create(name=name)
            kitchens[key] = k

        # Данные рецептов: (name, description, calories, meal_type, goal_suitability, cost_level, kitchen_key, ingredients)
        # ingredients: list of (ing_name, amount, unit)
        recipes_data = [
            # === ЗАВТРАКИ (breakfast) ===
            # Для maintain
            (
                'Омлет с помидорами и сыром',
                'Воздушный омлет со свежими помидорами и твёрдым сыром. Идеальный завтрак для поддержания формы.',
                320, 'breakfast', 'maintain', 2, 'Европейская',
                [('Яйцо', 4, 'шт'), ('Помидор', 150, 'гр'), ('Сыр твёрдый', 50, 'гр'), ('Масло сливочное', 10, 'гр')]
            ),
            (
                'Овсянка с фруктами и орехами',
                'Классическая овсяная каша с яблоком, бананом и грецкими орехами.',
                380, 'breakfast', 'maintain', 1, 'Европейская',
                [('Овсяные хлопья', 80, 'гр'), ('Яблоко', 1, 'шт'), ('Банан', 1, 'шт'), ('Орехи грецкие', 30, 'гр'), ('Молоко', 200, 'мл')]
            ),
            # Для lose
            (
                'Белковый омлет со шпинатом',
                'Лёгкий белковый омлет со свежим шпинатом. Низкокалорийный завтрак для похудения.',
                180, 'breakfast', 'lose', 1, 'Европейская',
                [('Яйцо белок', 4, 'шт'), ('Шпинат', 100, 'гр'), ('Сметана 10%', 30, 'гр')]
            ),
            # Для gain
            (
                'Сырники со сметаной',
                'Пышные творожные сырники со сметаной. Высокобелковый завтрак для набора массы.',
                520, 'breakfast', 'gain', 2, 'Русская',
                [('Творог', 300, 'гр'), ('Яйцо', 2, 'шт'), ('Мука', 50, 'гр'), ('Сахар', 30, 'гр'), ('Сметана', 100, 'гр')]
            ),
            # Универсальный завтрак
            (
                'Гренки с яйцом',
                'Классические гренки с яйцом. Быстрый и сытный завтрак.',
                400, 'breakfast', 'any', 1, 'Европейская',
                [('Хлеб', 100, 'гр'), ('Яйцо', 2, 'шт'), ('Молоко', 50, 'мл'), ('Масло сливочное', 15, 'гр')]
            ),

            # === ОБЕДЫ (lunch) ===
            # Для maintain
            (
                'Куриное филе с рисом',
                'Отварное куриное филе с рассыпчатым рисом и овощами. Сбалансированный обед.',
                450, 'lunch', 'maintain', 2, 'Европейская',
                [('Куриное филе', 200, 'гр'), ('Рис', 100, 'гр'), ('Морковь', 50, 'гр'), ('Лук репчатый', 50, 'гр')]
            ),
            (
                'Паста с индейкой',
                'Макароны из твёрдых сортов с тушёной индейкой в томатном соусе.',
                480, 'lunch', 'maintain', 2, 'Итальянская',
                [('Паста', 100, 'гр'), ('Филе индейки', 180, 'гр'), ('Помидоры', 150, 'гр'), ('Чеснок', 10, 'гр')]
            ),
            # Для lose
            (
                'Суп куриный с овощами',
                'Лёгкий куриный бульон с овощами. Идеально для похудения.',
                220, 'lunch', 'lose', 1, 'Русская',
                [('Куриное филе', 150, 'гр'), ('Картофель', 100, 'гр'), ('Морковь', 50, 'гр'), ('Лук', 50, 'гр'), ('Капуста', 50, 'гр')]
            ),
            # Для gain
            (
                'Гречка с котлетами',
                'Наваристая гречка с мясными котлетами. Сытный обед для набора массы.',
                650, 'lunch', 'gain', 2, 'Русская',
                [('Гречка', 120, 'гр'), ('Фарш мясной', 200, 'гр'), ('Лук', 50, 'гр'), ('Яйцо', 1, 'шт'), ('Хлеб', 30, 'гр')]
            ),
            # Универсальный обед
            (
                'Борщ с говядиной',
                'Классический русский борщ с говядиной. Наваристый и сытный.',
                380, 'lunch', 'any', 2, 'Русская',
                [('Говядина', 150, 'гр'), ('Свёкла', 100, 'гр'), ('Капуста', 80, 'гр'), ('Картофель', 100, 'гр'), ('Морковь', 50, 'гр'), ('Лук', 50, 'гр')]
            ),

            # === УЖИНЫ (dinner) ===
            # Для maintain
            (
                'Рыба запечённая с овощами',
                'Белая рыба, запечённая с сезонными овощами. Легкий и полезный ужин.',
                350, 'dinner', 'maintain', 2, 'Европейская',
                [('Рыба белая', 250, 'гр'), ('Брокколи', 100, 'гр'), ('Цветная капуста', 100, 'гр'), ('Лимон', 30, 'гр')]
            ),
            (
                'Салат с тунцом',
                'Свежий салат с тунцом, яйцом и овощами. Белковый ужин.',
                320, 'dinner', 'maintain', 2, 'Средиземноморская',
                [('Тунец консервированный', 150, 'гр'), ('Яйцо', 2, 'шт'), ('Огурец', 100, 'гр'), ('Помидор', 100, 'гр'), ('Листья салата', 50, 'гр')]
            ),
            # Для lose
            (
                'Куриный салат с зеленью',
                'Лёгкий салат с отварной курицей и свежей зеленью.',
                200, 'dinner', 'lose', 1, 'Европейская',
                [('Куриное филе', 150, 'гр'), ('Огурец', 100, 'гр'), ('Помидор', 100, 'гр'), ('Зелень', 30, 'гр')]
            ),
            # Для gain
            (
                'Говядина с картофельным пюре',
                'Тушёная говядина с нежным картофельным пюре. Сытный ужин для набора массы.',
                600, 'dinner', 'gain', 2, 'Русская',
                [('Говядина', 250, 'гр'), ('Картофель', 300, 'гр'), ('Молоко', 100, 'мл'), ('Масло сливочное', 20, 'гр'), ('Лук', 50, 'гр')]
            ),
            # Универсальный ужин
            (
                'Овощное рагу',
                'Разноцветное овощное рагу со специями. Полезный ужин.',
                280, 'dinner', 'any', 1, 'Европейская',
                [('Картофель', 150, 'гр'), ('Морковь', 80, 'гр'), ('Лук', 50, 'гр'), ('Баклажан', 100, 'гр'), ('Помидор', 100, 'гр')]
            ),

            # === ПЕРЕКУСЫ (snack) ===
            # Для maintain
            (
                'Йогурт с фруктами',
                'Натуральный йогурт со свежими фруктами.',
                180, 'snack', 'maintain', 1, 'Европейская',
                [('Йогурт натуральный', 200, 'гр'), ('Яблоко', 1, 'шт'), ('Мёд', 15, 'гр')]
            ),
            # Для lose
            (
                'Яблочные чипсы',
                'Хрустящие яблочные чипсы. Лёгкий перекус для похудения.',
                120, 'snack', 'lose', 1, 'Европейская',
                [('Яблоко', 200, 'гр')]
            ),
            # Для gain
            (
                'Сэндвич с авокадо',
                'Питательный сэндвич с авокадо и сыром.',
                380, 'snack', 'gain', 2, 'Европейская',
                [('Хлеб цельнозерновой', 80, 'гр'), ('Авокадо', 100, 'гр'), ('Сыр', 40, 'гр')]
            ),
            # Универсальный перекус
            (
                'Ореховая смесь',
                'Разнообразные орехи. Быстрый и полезный перекус.',
                300, 'snack', 'any', 2, 'Разное',
                [('Орехи грецкие', 30, 'гр'), ('Орехи миндаль', 30, 'гр'), ('Орехи кешью', 30, 'гр')]
            ),

            # === ДОПОЛНИТЕЛЬНЫЕ РЕЦЕПТЫ (any) ===
            (
                'Каша рисовая с молоком',
                'Классическая рисовая каша на молоке с сахаром.',
                250, 'any', 'any', 1, 'Русская',
                [('Рис', 60, 'гр'), ('Молоко', 200, 'мл'), ('Сахар', 20, 'гр'), ('Масло сливочное', 10, 'гр')]
            ),
        ]

        created_count = 0
        skipped_count = 0

        for recipe_data in recipes_data:
            name, desc, calories, meal_type, goal, cost, kitchen_name, ingredients = recipe_data

            # Проверка существования
            if Recipes.objects.filter(name=name).exists():
                self.stdout.write(f'⊘ Пропущен (существует): {name}')
                skipped_count += 1
                continue

            # Получаем кухню
            kitchen, _ = Kitchenname.objects.get_or_create(name=kitchen_name)

            # Создаём рецепт
            recipe = Recipes.objects.create(
                name=name[:50],
                description=desc,
                calories=calories,
                meal_type=meal_type,
                goal_suitability=goal,
                cost_level=cost,
                KitchennameId=kitchen,
            )

            # Добавляем ингредиенты
            for ing_name, amount, unit in ingredients:
                ingredient, _ = Ingredients.objects.get_or_create(name=ing_name, defaults={'unit': unit})
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )

            self.stdout.write(f'✓ Создан: {name} | {meal_type} | {goal} | {calories} ккал')
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n{"="*50}'))
        self.stdout.write(self.style.SUCCESS(f'Готово! Создано: {created_count}, пропущено: {skipped_count}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*50}\n'))

        # Статистика
        from django.db.models import Count
        self.stdout.write('📊 Статистика по БД:')
        self.stdout.write('\nПо meal_type:')
        for mt in ['breakfast', 'lunch', 'dinner', 'snack', 'any']:
            count = Recipes.objects.filter(meal_type=mt).count()
            self.stdout.write(f'  {mt}: {count}')

        self.stdout.write('\nПо goal_suitability:')
        for goal in ['lose', 'maintain', 'gain', 'any']:
            count = Recipes.objects.filter(goal_suitability=goal).count()
            self.stdout.write(f'  {goal}: {count}')

        self.stdout.write('\nПо комбинации meal_type + goal_suitability:')
        for mt in ['breakfast', 'lunch', 'dinner', 'snack']:
            self.stdout.write(f'  {mt}:')
            for goal in ['lose', 'maintain', 'gain', 'any']:
                count = Recipes.objects.filter(meal_type=mt, goal_suitability=goal).count()
                self.stdout.write(f'    + {goal}: {count}')

        self.stdout.write('\nПо cost_level:')
        for level in [1, 2, 3]:
            count = Recipes.objects.filter(cost_level=level).count()
            level_name = {1: 'Эконом', 2: 'Средний', 3: 'Премиум'}.get(level)
            self.stdout.write(f'  {level_name}: {count}')
