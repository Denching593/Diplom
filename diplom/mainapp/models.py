from django.contrib.auth.models import User
from django.db import models

class UserProfile(User):
    diet_type = models.CharField(max_length=100, blank=True, null=True)

    def get_preferences(self):
        """Возвращает все предпочтения пользователя"""
        return UserPreference.objects.filter(user=self)

    def get_favorite_recipes(self):
        """Возвращает все избранные рецепты пользователя"""
        return Recipes.objects.filter(favorite__user=self)

    



# Имя кухни(русская, китайская и тд)
class Kitchenname(models.Model):
    name = models.CharField(max_length=50 , verbose_name='Название')

    @classmethod
    def get_all_kitchens(cls):
        """Возвращает все доступные кухни"""
        return cls.objects.all()


class Recipes(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('dinner', 'Ужин'),
        ('snack', 'Перекус'),
        ('any', 'Любой'),
    ]

    GOAL_SUITABILITY = [
        ('lose', 'Похудение'),
        ('maintain', 'Поддержание'),
        ('gain', 'Набор массы'),
        ('any', 'Любая цель'),
    ]

    COST_LEVELS = [
        (1, 'Эконом'),
        (2, 'Средний'),
        (3, 'Премиум'),
    ]

    name = models.CharField(max_length=50 , verbose_name= 'Название')
    description = models.TextField(verbose_name='Описание')
    calories = models.IntegerField(verbose_name='Калорийность' )
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    KitchennameId = models.ForeignKey(Kitchenname, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, default='any', verbose_name='Тип приёма пищи')
    goal_suitability = models.CharField(max_length=20, choices=GOAL_SUITABILITY, default='any', verbose_name='Подходит для цели')
    cost_level = models.IntegerField(choices=COST_LEVELS, default=2, verbose_name='Уровень стоимости')
    spoonacular_id = models.IntegerField(null=True, blank=True, unique=True, verbose_name='ID в Spoonacular')

    def __str__(self):
        return f"{self.name} ({self.calories} ккал)"

    def get_ingredients_list(self):
        """Возвращает список ингредиентов с количеством для рецепта"""
        return [
            {'ingredient': ri.ingredient.name, 'amount': ri.amount, 'unit': ri.ingredient.unit}
            for ri in self.recipeingredient_set.all()
        ]

    def is_suitable_for_goal(self, goal):
        """Проверяет, подходит ли рецепт для цели пользователя"""
        if self.goal_suitability == 'any':
            return True
        return self.goal_suitability == goal

class Ingredients(models.Model):
    name = models.CharField(max_length=50 , verbose_name='Название')
    unit = models.CharField(max_length=50 , verbose_name='Количество (гр или шт)' , null=True ,   blank=True)
    image = models.ImageField(upload_to='ingridients/', null=True ,   blank=True)

    @classmethod
    def get_by_name(cls, name):
        """Ищет ингредиент по имени (частичное совпадение)"""
        return cls.objects.filter(name__icontains=name)

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE )
    ingredient = models.ForeignKey(Ingredients, on_delete=models.CASCADE)
    amount = models.FloatField()

    def get_full_ingredient_info(self):
        """Возвращает полную информацию об ингредиенте с количеством"""
        return {
            'name': self.ingredient.name,
            'amount': self.amount,
            'unit': self.ingredient.unit,
            'image': self.ingredient.image
        }

#избранное
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE)

    @classmethod
    def add_to_favorites(cls, user, recipe):
        """Добавляет рецепт в избранное"""
        return cls.objects.create(user=user, recipe=recipe)

    def remove_from_favorites(self):
        """Удаляет рецепт из избранного"""
        self.delete()

class UserPreference(models.Model):
    PREFERENCE_CHOICES = [
        ('like', 'Нравится'),
        ('dislike', 'Не нравится'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredients, on_delete=models.CASCADE , verbose_name='Ингредиенты')
    preference_type = models.CharField(max_length=10, choices=PREFERENCE_CHOICES )

    class Meta:
        unique_together = ('user', 'ingredient')
        verbose_name = 'Предпочтение пользователя'
        verbose_name_plural = 'Предпочтения пользователей'

    @classmethod
    def get_user_preferences(cls, user):
        """Возвращает все предпочтения пользователя"""
        return cls.objects.filter(user=user)

    def is_liked(self):
        """Проверяет, нравится ли пользователю ингредиент"""
        return self.preference_type == 'like'


class UserSettings(models.Model):
    """Настройки пользователя по умолчанию"""
    BUDGET_TIERS = [
        ('economy', 'Эконом'),
        ('medium', 'Средний'),
        ('premium', 'Премиум'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    budget_tier = models.CharField(max_length=20, choices=BUDGET_TIERS, default='medium', verbose_name='Бюджет')
    default_goal = models.CharField(max_length=20, default='maintain', verbose_name='Цель по умолчанию')
    default_calories = models.IntegerField(default=2000, verbose_name='Калории по умолчанию')

    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'

    def __str__(self):
        return f"Настройки {self.user.username}"

    def get_budget_level(self):
        """Возвращает числовой уровень бюджета"""
        budget_map = {'economy': 1, 'medium': 2, 'premium': 3}
        return budget_map.get(self.budget_tier, 2)

    def update_defaults(self, goal=None, calories=None, budget=None):
        """Обновляет настройки по умолчанию"""
        if goal:
            self.default_goal = goal
        if calories:
            self.default_calories = calories
        if budget:
            self.budget_tier = budget
        self.save()


class ShoppingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredients, on_delete=models.CASCADE ,  verbose_name='Ингредиенты')
    amount = models.IntegerField()
    is_checked = models.BooleanField(default=False)

    @classmethod
    def get_user_shopping_list(cls, user):
        """Возвращает список покупок пользователя (не отмеченные)"""
        return cls.objects.filter(user=user, is_checked=False)

    def mark_as_checked(self):
        """Отмечает товар как купленный"""
        self.is_checked = True
        self.save()


class CookingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE)
    cooked_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_user_history(cls, user, limit=10):
        """Возвращает историю готовки пользователя"""
        return cls.objects.filter(user=user).order_by('-cooked_at')[:limit]

    @classmethod
    def get_most_cooked_recipes(cls, user, limit=5):
        """Возвращает самые часто готовившиеся рецепты"""
        from django.db.models import Count
        return Recipes.objects.filter(
            cookinghistory__user=user
        ).annotate(count=Count('cookinghistory')).order_by('-count')[:limit]


class MealPlan(models.Model):
    """План рациона питания пользователя"""
    BUDGET_TIERS = [
        ('economy', 'Эконом'),
        ('medium', 'Средний'),
        ('premium', 'Премиум'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    goal = models.CharField(max_length=20, verbose_name='Цель')  # lose, maintain, gain
    target_calories = models.IntegerField(verbose_name='Целевые калории')
    budget_tier = models.CharField(max_length=20, choices=BUDGET_TIERS, default='medium', verbose_name='Бюджет')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_saved = models.BooleanField(default=False, verbose_name='Сохранён')

    class Meta:
        verbose_name = 'План питания'
        verbose_name_plural = 'Планы питания'
        ordering = ['-created_at']

    def __str__(self):
        return f"План {self.user.username} — {self.target_calories} ккал ({self.created_at.strftime('%d.%m.%Y')})"

    def get_weekly_meals(self):
        """Возвращает все приёмы пищи для плана"""
        return self.items.all().order_by('day', 'meal_type')

    def get_total_calories(self):
        """Считает общую калорийность плана за день"""
        total = 0
        for item in self.items.all():
            total += item.recipe.calories * item.portion
        return total


class MealPlanItem(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('dinner', 'Ужин'),
        ('snack', 'Перекус'),
    ]

    DAYS_OF_WEEK = [
        ('mon', 'Понедельник'),
        ('tue', 'Вторник'),
        ('wed', 'Среда'),
        ('thu', 'Четверг'),
        ('fri', 'Пятница'),
        ('sat', 'Суббота'),
        ('sun', 'Воскресенье'),
    ]

    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='items', verbose_name='План')
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE, verbose_name='Рецепт')
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK, verbose_name='День')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, verbose_name='Тип приёма пищи')
    portion = models.FloatField(default=1.0, verbose_name='Порция')

    class Meta:
        verbose_name = 'Приём пищи в плане'
        verbose_name_plural = 'Приёмы пищи в плане'

    def __str__(self):
        return f"{self.get_day_display()} — {self.get_meal_type_display()}: {self.recipe.name}"

    def get_adjusted_ingredients(self):
        """Возвращает ингредиенты с учётом размера порции"""
        return [
            {
                'ingredient': ri.ingredient.name,
                'amount': ri.amount * self.portion,
                'unit': ri.ingredient.unit
            }
            for ri in self.recipe.recipeingredient_set.all()
        ]

    def get_full_meal_info(self):
        """Возвращает полную информацию о приёме пищи"""
        return {
            'day': self.get_day_display(),
            'meal_type': self.get_meal_type_display(),
            'recipe': self.recipe.name,
            'calories': self.recipe.calories * self.portion,
            'portion': self.portion
        }