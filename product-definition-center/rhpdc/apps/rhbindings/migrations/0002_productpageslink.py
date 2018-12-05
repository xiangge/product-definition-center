# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0002_auto_20150512_0719'),
        ('rhbindings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductPagesLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('product_pages_id', models.PositiveIntegerField()),
                ('release', models.OneToOneField(related_name='product_pages_link', to='release.Release')),
            ],
        ),
    ]
