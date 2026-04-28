from django.contrib.auth.models import User
from django.db import models

class UserProfile(User):
    diet_type = models.CharField(max_length=100, blank=True, null=True)




# Имя кухни(русская, китайская и тд)
class Kitchenname(models.Model):
    name = models.CharField(max_length=50 , verbose_name='Название')


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

class Ingredients(models.Model):
    name = models.CharField(max_length=50 , verbose_name='Название')
    unit = models.CharField(max_length=50 , verbose_name='Количество (гр или шт)' , null=True ,   blank=True)
    image = models.ImageField(upload_to='ingridients/', null=True ,   blank=True)

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE )
    ingredient = models.ForeignKey(Ingredients, on_delete=models.CASCADE)
    amount = models.FloatField()

#избранное
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE)

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

class ShoppingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredients, on_delete=models.CASCADE ,  verbose_name='Ингредиенты')
    amount = models.IntegerField()
    is_checked = models.BooleanField(default=False)

class CookingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipes, on_delete=models.CASCADE)
    cooked_at = models.DateTimeField(auto_now_add=True)


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