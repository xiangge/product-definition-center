# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0002_auto_20150512_0719'),
        ('rhbindings', '0002_productpageslink'),
    ]

    operations = [
        migrations.CreateModel(
            name='Errata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('product_version', models.CharField(max_length=200, null=True, blank=True)),
                ('release', models.OneToOneField(to='release.Release')),
            ],
        ),
    ]
