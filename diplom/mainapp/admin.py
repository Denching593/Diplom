from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Recipes)
admin.site.register(Kitchenname)
admin.site.register(Ingredients)
admin.site.register(MealPlan)
admin.site.register(MealPlanItem)
admin.site.register(UserSettings)
admin.site.register(UserPreference)
admin.site.register(ShoppingList)
admin.site.register(Favorite)
admin.site.register(CookingHistory)
admin.site.register(RecipeIngredient)