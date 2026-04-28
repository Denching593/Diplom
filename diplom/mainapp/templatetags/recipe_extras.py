from django import template

register = template.Library()

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
