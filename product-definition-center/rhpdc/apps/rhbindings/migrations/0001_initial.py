# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('release', '0002_auto_20150512_0719'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrewTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag_name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ReleaseBrewMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('default_target', models.CharField(max_length=200, null=True, blank=True)),
                ('release', models.OneToOneField(related_name='brew_mapping', to='release.Release')),
            ],
        ),
        migrations.AddField(
            model_name='brewtag',
            name='brew_mapping',
            field=models.ForeignKey(related_name='allowed_tags', to='rhbindings.ReleaseBrewMapping'),
        ),
        migrations.AlterUniqueTogether(
            name='brewtag',
            unique_together=set([('brew_mapping', 'tag_name')]),
        ),
    ]
