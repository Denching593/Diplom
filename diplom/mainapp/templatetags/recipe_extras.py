from django import template
from django.utils.html import strip_tags

register = template.Library()


@register.filter
def remove_html_tags(value):
    """Удаляет HTML-теги из строки"""
    if not value:
        return ''
    return strip_tags(value)


CUISINE_TRANSLATIONS = {
    'Asian': 'Азиатская',
    'Chinese': 'Китайская',
    'Japanese': 'Японская',
    'Korean': 'Корейская',
    'Thai': 'Тайская',
    'Vietnamese': 'Вьетнамская',
    'Indian': 'Индийская',
    'Middle Eastern': 'Ближневосточная',
    'Mediterranean': 'Средиземноморская',
    'European': 'Европейская',
    'French': 'Французская',
    'Italian': 'Итальянская',
    'Spanish': 'Испанская',
    'Greek': 'Греческая',
    'German': 'Немецкая',
    'British': 'Британская',
    'Eastern European': 'Восточноевропейская',
    'Russian': 'Русская',
    'Polish': 'Польская',
    'Hungarian': 'Венгерская',
    'American': 'Американская',
    'Mexican': 'Мексиканская',
    'South American': 'Южноамериканская',
    'African': 'Африканская',
    'Nordic': 'Скандинавская',
    'Australian': 'Австралийская',
    'Caribbean': 'Карибская',
    'Cajun': 'Каджунская',
    'Southern/Soul Food': 'Южная кухня',
    'Pacific Rim': 'Тихоокеанская',
}


@register.filter
def translate_cuisine(value):
    """Переводит название кухни на русский"""
    return CUISINE_TRANSLATIONS.get(value, value)


@register.filter
def translate_cuisines_list(values):
    """Переводит список названий кухонь и возвращает строку"""
    if not values:
        return ''
    translated = [CUISINE_TRANSLATIONS.get(v, v) for v in values]
    return ', '.join(translated)


UNIT_TRANSLATIONS = {
    'oz': 'унц', 'ounce': 'унц', 'ounces': 'унц',
    'tbsp': 'ст.л.', 'tablespoon': 'ст.л.', 'tablespoons': 'ст.л.',
    'tsp': 'ч.л.', 'teaspoon': 'ч.л.', 'teaspoons': 'ч.л.',
    'lb': 'фунт', 'lbs': 'фунт', 'pound': 'фунт', 'pounds': 'фунт',
    'g': 'г', 'gram': 'г', 'grams': 'г',
    'kg': 'кг', 'kilogram': 'кг', 'kilograms': 'кг',
    'mg': 'мг', 'milligram': 'мг', 'milligrams': 'мг',
    'ml': 'мл', 'milliliter': 'мл', 'milliliters': 'мл',
    'l': 'л', 'liter': 'л', 'liters': 'л', 'litre': 'л', 'litres': 'л',
    'c': 'ст.', 'cup': 'ст.', 'cups': 'ст.',
    'fl oz': 'жид.унц', 'fluid ounce': 'жид.унц', 'fluid ounces': 'жид.унц',
    'qt': 'кв.', 'quart': 'кв.', 'quarts': 'кв.',
    'pt': 'пинта', 'pint': 'пинта', 'pints': 'пинта',
    'gal': 'гал.', 'gallon': 'гал.', 'gallons': 'гал.',
    'stalk': 'стеб.', 'stalks': 'стеб.',
    'serving': 'порц.', 'servings': 'порц.',
    'slice': 'ломт.', 'slices': 'ломт.',
    'clove': 'зубч.', 'cloves': 'зубч.',
    'pinch': 'щеп.', 'pinches': 'щеп.',
    'can': 'бан.', 'cans': 'бан.',
    'package': 'уп.', 'packages': 'уп.',
    'bunch': 'пуч.', 'bunches': 'пуч.',
    'sprig': 'вет.', 'sprigs': 'вет.',
    'head': 'гол.', 'heads': 'гол.',
    'piece': 'шт.', 'pieces': 'шт.',
    'stick': 'пал.', 'sticks': 'пал.',
    'leaf': 'лист', 'leaves': 'лист',
    'dash': 'щеп.', 'dashes': 'щеп.',
    'drop': 'кап.', 'drops': 'кап.',
    'handful': 'горст.', 'handfuls': 'горст.',
    'large': 'бол.', 'medium': 'сред.', 'small': 'мал.',
    'thin': 'тонк.', 'thick': 'толст.',
    'whole': 'цел.',
}


@register.filter
def translate_unit(value):
    """Переводит английские единицы измерения на русский"""
    if not value:
        return ''
    key = value.strip().lower()
    return UNIT_TRANSLATIONS.get(key, value)
