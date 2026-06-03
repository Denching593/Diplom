@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python manage.py shell -c "
from mainapp.models import Recipes, Kitchenname
k, _ = Kitchenname.objects.get_or_create(name='Russkaya')
print('Kitchen OK:', k.name)
print('Total recipes:', Recipes.objects.count())
"
pause
