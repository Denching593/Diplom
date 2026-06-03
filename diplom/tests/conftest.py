"""
Конфигурация pytest для Django проекта
"""
import pytest
import os
import django

# Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diplom.settings')
django.setup()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включаем доступ к БД для всех тестов"""
    pass
