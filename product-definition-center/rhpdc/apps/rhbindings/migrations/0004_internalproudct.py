# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0002_auto_20150512_0719'),
        ('rhbindings', '0003_errata'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternalProudct',
            fields=[
                ('product', models.OneToOneField(related_name='internal', primary_key=True, serialize=False, to='release.Product')),
            ],
        ),
    ]
