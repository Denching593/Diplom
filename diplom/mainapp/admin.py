from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(Recipes)
class RecipesAdmin(admin.ModelAdmin):
    list_display = ('name', 'calories', 'meal_type', 'goal_suitability', 'cost_level', 'KitchennameId')
    list_filter = ('cost_level', 'meal_type', 'goal_suitability', 'KitchennameId')
    search_fields = ('name',)

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