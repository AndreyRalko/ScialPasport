from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def trans_db(value):
    if not value:
        return value
    return _(str(value))
