# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('component', '0012_auto_20160928_1838'),
        ('partners', '0003_partner_compose_arches'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='errata_packages',
            field=models.ManyToManyField(default=[], to='component.GlobalComponent', blank=True),
        ),
    ]
