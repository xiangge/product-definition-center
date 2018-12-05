# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_auto_20150512_0703'),
        ('partners', '0002_auto_20151015_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='compose_arches',
            field=models.ManyToManyField(default=[], to='common.Arch', blank=True),
        ),
    ]
