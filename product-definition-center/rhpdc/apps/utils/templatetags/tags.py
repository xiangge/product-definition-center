from django import template

import pdc
from rhpdc import get_version


def pdc_version():
    return 'Version: ' + get_version() + ' based on upstream ' + pdc.get_version()


register = template.Library()

register.simple_tag(pdc_version)
