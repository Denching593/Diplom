"""
URL configuration for diplom project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from mainapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.log_in, name='log_in'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),

    # API для профиля
    path('api/favorites/remove/<int:fav_id>/', views.remove_favorite, name='remove_favorite'),
    path('api/meal-plan/delete/<int:plan_id>/', views.delete_meal_plan, name='delete_meal_plan'),
    path('api/shopping-list/toggle/<int:item_id>/', views.toggle_shopping_item, name='toggle_shopping_item'),
    path('api/shopping-list/delete/<int:item_id>/', views.delete_shopping_item, name='delete_shopping_item'),
    path('api/shopping-list/clear/', views.clear_shopping_list, name='clear_shopping_list'),
    path('compose/', views.compose_dish, name='compose_dish'),
    path('meal-plan/', views.meal_plan, name='meal_plan'),
    path('api/search_recipes/', views.search_recipes, name='search_recipes'),
    path('recipe/<str:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipe/<str:recipe_id>/cooking/', views.recipe_cooking, name='recipe_cooking'),
    path('api/recipe/fetch/<str:recipe_id>/', views.fetch_recipe_from_api, name='fetch_recipe_from_api'),

    # API для рациона питания
    path('api/meal-plan/generate/', views.generate_meal_plan, name='generate_meal_plan'),
    path('api/meal-plan/save/', views.save_meal_plan, name='save_meal_plan'),
    path('api/meal-plan/saved/', views.get_saved_meal_plans, name='get_saved_meal_plans'),
    path('api/shopping-list/generate/', views.generate_shopping_list, name='generate_shopping_list'),
    path('api/shopping-list/', views.get_shopping_list, name='get_shopping_list'),
    path('api/favorites/save/', views.save_to_favorites, name='save_to_favorites'),
    #path('get_ingredients/', views.get_ingredients, name='get_ingredients'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)