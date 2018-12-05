# -- coding: utf-8 -*-
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model


# predefined superuser list that can log into the admin site
superuser_list = [
    'sochotni',
    'lsedlar',
    'dmach',
    'xchu',
    'jiahuang',
    'ycheng',
    'chuzhang',
    'bliu',
]

# Predefined Group Apps Maps
# Will add all permissions belongs to these apps to target group,
# including '%(app_label)s.add_%(model_name)s',
#           '%(app_label)s.change_%(model_name)s'
#           '%(app_label)s.delete_%(model_name)s'
group_apps_map = {
    # Add groups and apps you want to import below
    'devel': ['contact', 'component'],
    'eng-rcm': ['common', 'compose', 'package', 'release', 'repository']
}

# hosts/keytabs of eng-rcm
hosts_keytabs = [
    'distill/rcm-rhel5.app.eng.bos.redhat.com',
    'distill/rcm-rhel6.app.eng.bos.redhat.com',
    'distill/rcm-rhel7.app.eng.bos.redhat.com',
    'distill/rcm-scl.app.eng.bos.redhat.com',
    'distill/rcm-sat.app.eng.bos.redhat.com',
    'distill/rcm-dev.app.eng.bos.redhat.com',
    'distill/rcm-worker-1.app.eng.bos.redhat.com',
    'distill/rcm-worker-2.app.eng.bos.redhat.com'
]

if __name__ == "__main__":
    # insert superusers
    for user_name in superuser_list:
        user, created = get_user_model().objects.get_or_create(username=user_name)
        if created:
            user.set_unusable_password()
        user.is_staff = True
        user.is_superuser = True
        user.save()

    # import predefined group permissions
    for group_name, apps_list in group_apps_map.iteritems():
        group, created = Group.objects.get_or_create(name=group_name)
        total_perms = []
        for app in apps_list:
            perms = Permission.objects.filter(content_type__app_label=app)
            total_perms += perms
        group.permissions.add(*total_perms)

    # Add hosts/keytabs to group eng-rcm
    group = Group.objects.get(name='eng-rcm')
    for keytab in hosts_keytabs:
        user, created = get_user_model().objects.get_or_create(username=keytab)
        if created:
            user.set_unusable_password()
            user.save()
        user.groups.add(group)
