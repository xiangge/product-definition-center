#!/usr/bin/python


import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from django.conf import settings
settings.REST_FRAMEWORK["PAGINATE_BY"] = 100000

from django.core.urlresolvers import reverse
from rest_framework.test import APIClient

from pdc.apps.common.test_utils import create_user

# Set this flag to True if need to check the debug message
debug = False

# Below exception will be thrown out(implicitly) if DEBUG in the settings file is set to False (default value of
# Stage/Prod), which means that this script could not be run successful in Stage/Prod but return 400.
# DisallowedHost("Invalid HTTP_HOST header: 'testserver'. You may need to add u'testserver' to ALLOWED_HOSTS.")
# Another solution we could configure ALLOWED_HOSTS with ['*'] or append 'testserver' to accept the request from this
# kind of HOSTs, but considering security, the ALLOWED_HOSTS is only configured with server's hostname, what's more,
# eng-ops team won't allowed to make such configuration.
# To be compatible with servers and local importing, we temp set the DEBUG setting to True, but reset its value back
# to its original one at the end.
original = settings.DEBUG
settings.DEBUG = False
settings.ALLOWED_HOSTS = ['*']

client = APIClient()
client.force_authenticate(create_user('admin', perms=['pdc.admin'], is_super=True))


def print_debug_message(msg, response):
    if debug:
        print '%s: %d' % (msg, response.status_code)


def link_compose_to_release(compose_id, release_id):
    url = reverse('compose-detail', args=[compose_id])
    response = client.get(url)
    assert response.status_code == 200
    linked_releases = response.data['linked_releases']
    linked_releases.append(release_id)
    response = client.patch(url, {'linked_releases': linked_releases}, format='json')
    assert response.status_code == 200
    print_debug_message('link %s to %s' % (compose_id, release_id), response)

# rhel-7.0-updates
r = client.post(
    reverse('releaseclone-list'),
    {'old_release_id': 'rhel-7.0', 'release_type': 'updates'},
    format="json",
)
print_debug_message('rhel-7.0-updates post', r)

# link rhel-7.0 GA compose to rhel-7.0-updates
link_compose_to_release('RHEL-7.0-20140507.0', 'rhel-7.0-updates')

# TODO: skip beta and htb, possibly shadow
r = client.post(
    reverse('repoclone-list'),
    {'release_id_from': 'rhel-7.0', 'release_id_to': 'rhel-7.0-updates'},
    format='json',
)
print_debug_message('rhel-7.0 clone all repos post', r)

# rhel-7.1-updates
r = client.post(
    reverse('releaseclone-list'),
    {'old_release_id': 'rhel-7.1', 'release_type': 'updates'},
    format='json',
)
print_debug_message('rhel-7.1-updates post', r)

# link rhel-7.1 GA compose to rhel-7.1-updates
link_compose_to_release('RHEL-7.1-20150219.1', 'rhel-7.1-updates')

# TODO: skip beta and htb, possibly shadow
r = client.post(
    reverse('repoclone-list'),
    {'release_id_from': 'rhel-7.1', 'release_id_to': 'rhel-7.1-updates'},
    format='json',
)
print_debug_message('rhel-7.1 clone all repos post', r)

# rhel-7.1-eus
# TODO: filter variants & arches
r = client.post(
    reverse('releaseclone-list'),
    {'old_release_id': 'rhel-7.1', 'release_type': 'eus'},
    format="json",
)
print_debug_message('rhel-7.1-eus post', r)

# link rhel-7.1 GA compose to rhel-7.1-eus
link_compose_to_release('RHEL-7.1-20150219.1', 'rhel-7.1-eus')

# TODO: skip beta and htb, possibly shadow
# TODO: filter variants & arches
r = client.get(
    reverse('contentdeliveryrepos-list'),
    {'release_id': 'rhel-7.1', "page_size": 1000},
    format='json',
)
print_debug_message('rhel-7.1 get', r)
new_repos = []
for i in r.data["results"]:
    i["release_id"] = "rhel-7.1-eus"
    if i["shadow"]:
        continue
    if i["repo_family"] != "dist":
        continue
    if "Server" not in i["variant_uid"]:
        continue
    if i["service"] == "rhn":
        if i["name"].endswith("-7"):
            i["name"] += ".1.z"
        else:
            i["name"] = i["name"].replace("-7-", "-7.1.z-")
    if i["service"] == "pulp":
        pass
        # TODO: rename doesn't work, populate with real pulp repos
    del i['id']
    new_repos.append(i)
# TODO: bulk insert
for i in new_repos:
    r = client.post(
        reverse('contentdeliveryrepos-list'),
        i,
        format="json",
    )

# Set original value for DEBUG from settings
settings.DEBUG = original
