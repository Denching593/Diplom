from django.core.management.base import BaseCommand
from mainapp.models import Recipes, Kitchenname

class Command(BaseCommand):
    help = 'Add premium recipes to the database'

    def handle(self, *args, **kwargs):
        # Get or create kitchens
        french_kitchen, _ = Kitchenname.objects.get_or_create(name='Французская')
        american_kitchen, _ = Kitchenname.objects.get_or_create(name='Американская')
        mediterranean_kitchen, _ = Kitchenname.objects.get_or_create(name='Средиземноморская')
        italian_kitchen, _ = Kitchenname.objects.get_or_create(name='Итальянская')
        russian_kitchen, _ = Kitchenname.objects.get_or_create(name='Русская')
        chinese_kitchen, _ = Kitchenname.objects.get_or_create(name='Китайская')
        japanese_kitchen, _ = Kitchenname.objects.get_or_create(name='Японская')

        kitchens = {
            'french': french_kitchen,
            'american': american_kitchen,
            'mediterranean': mediterranean_kitchen,
            'italian': italian_kitchen,
            'russian': russian_kitchen,
            'chinese': chinese_kitchen,
            'japanese': japanese_kitchen,
        }

        recipes_data = [
            # breakfast
            ('Омлет с лобстером и трюфельным маслом', 'Нежный французский омлет с мясом лобстера', 450, 'breakfast', 'gain', 3, 'french'),
            ('Блинчики с красной икрой', 'Тонкие ажурные блинчики с красной икрой', 380, 'breakfast', 'maintain', 3, 'russian'),
            ('Тосты с авокадо и лососем', 'Хрустящий тост с кремовым авокадо и лососем', 320, 'breakfast', 'lose', 3, 'mediterranean'),
            # lunch
            ('Стейк Рибай из мраморной говядины', 'Сочный стейк из мраморной говядины', 650, 'lunch', 'gain', 3, 'american'),
            ('Утка по-пекински', 'Классическое китайское блюдо - утка с хрустящей корочкой', 520, 'lunch', 'maintain', 3, 'chinese'),
            ('Стейк из тунца с кунжутом', 'Стейк из свежего тунца с кунжутной корочкой', 290, 'lunch', 'lose', 3, 'japanese'),
            # dinner
            ('Стейк из лосося со спаржей', 'Сочный стейк из атлантического лосося', 580, 'dinner', 'gain', 3, 'mediterranean'),
            ('Филе миньон с трюфельным пюре', 'Нежное филе миньон с картофельным пюре', 540, 'dinner', 'maintain', 3, 'french'),
            ('Тигровые креветки в чесночном масле', 'Крупные тигровые креветки в сливочном масле', 280, 'dinner', 'lose', 3, 'mediterranean'),
            # snack
            ('Капрезе с моцареллой буффало', 'Итальянская закуска с помидорами и моцареллой', 310, 'snack', 'maintain', 3, 'italian'),
            ('Сашими из лосося и тунца', 'Свежайшие ломтики лосося и тунца', 220, 'snack', 'lose', 3, 'japanese'),
            ('Кальмары гриль с чили', 'Кольца кальмара на гриле с перцем чили', 340, 'snack', 'gain', 3, 'mediterranean'),
        ]

        count = 0
        for name, desc, calories, meal_type, goal, cost, kitchen_key in recipes_data:
            recipe, created = Recipes.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'calories': calories,
                    'meal_type': meal_type,
                    'goal_suitability': goal,
                    'cost_level': cost,
                    'KitchennameId': kitchens[kitchen_key],
                    'image': '',
                    'spoonacular_id': None,
                }
            )
            if created:
                count += 1
                self.stdout.write(f'Создан: {name}')
            else:
                self.stdout.write(f'Уже существует: {name}')

        self.stdout.write(self.style.SUCCESS(f'\nВсего создано новых рецептов: {count}'))
