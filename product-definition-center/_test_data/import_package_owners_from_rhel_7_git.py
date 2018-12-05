# -- coding: utf-8 -*-

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

import re
from django.db import transaction
from pdc.apps.release.models import Release
from pdc.apps.contact.models import (Person,
                                     Maillist,
                                     ContactRole,
                                     GlobalComponentContact,
                                     ReleaseComponentContact)
from pdc.apps.component.models import ReleaseComponent, GlobalComponent
from pdc.apps.common import constants

# 'borrowed' from rhel-7.git
OWNER_SPLIT_RE = re.compile(r'^\s*(?P<package>[^\s]+)\s+(?P<owner>[^\s]+)(:?\s+(?P<mailinglist>[^\s]+@[^\s]+\.[^\s]+))?(:?\s+(?P<comment>#.*))?$')


def read_package_data(lines):
    """
    Convert lines to structured data.

    Input: * text lines with package ownership data or comments
    Output:
        * (comments, packages)
        * comments: list of any line comments found in the source lines
        * packages: sorted list of {package, owner, mailinglist, comment} dicts
    """
    comments = []
    packages = []

    for i in lines:
        i = i.strip()

        if not i:
            continue

        if i.startswith("#"):
            comments.append(i.lstrip("#").strip())
            continue

        match = OWNER_SPLIT_RE.match(i)
        if match is None:
            raise ValueError("Couldn't parse line: %s" % i)
        gd = match.groupdict()
        if "@" in gd["owner"] and gd["mailinglist"] is None:
            # HACK:
            gd["mailinglist"] = gd["owner"]
            gd["owner"] = "-"
        gd["mailinglist"] = gd.get("mailinglist") or ""
        gd["comment"] = gd.get("comment") or ""
        gd["comment"] = gd["comment"].lstrip("#").strip()
        packages.append(gd)

    packages.sort(lambda i, j: cmp(i["package"], j["package"]))
    return comments, packages


@transaction.atomic
def import_package_owner(path, release_id='rhel-7.0'):
    contacts = []
    inherited = 0

    lines = open(path, 'r').readlines()
    _, components = read_package_data(lines)

    build_contact_role, _ = ContactRole.objects.get_or_create(
        name=constants.BUILD_CONTACT)
    devel_contact_role, _ = ContactRole.objects.get_or_create(
        name=constants.DEVEL_CONTACT)

    release = Release.objects.get(release_id=release_id)

    process_count = 0
    for component in components:
        name = component['package']
        global_component, _ = GlobalComponent.objects.get_or_create(name=name)
        release_component, created = ReleaseComponent.objects.get_or_create(
            release=release,
            global_component=global_component,
            name=name
        )

        # New component, copy contacts from global component.
        if created:
            for gcontact in GlobalComponentContact.objects.filter(component=global_component):
                contacts.append(ReleaseComponentContact(
                    component=release_component,
                    role=gcontact.role,
                    contact=gcontact.contact
                ))
                inherited += 1

        if component.get('mailinglist'):
            devel_contact, _ = Maillist.objects.get_or_create(
                mail_name=component.get('mailinglist').split('@')[0],
                email=component.get('mailinglist')
            )
            contacts.append(ReleaseComponentContact(
                component=release_component,
                role=devel_contact_role,
                contact=devel_contact
            ))

        build_contact, _ = Person.objects.get_or_create(
            username=component.get('owner'),
            email=component.get('owner') + '@redhat.com'
        )
        contacts.append(ReleaseComponentContact(
            component=release_component,
            role=build_contact_role,
            contact=build_contact
        ))

        process_count += 1

    ReleaseComponentContact.objects.bulk_create(contacts)

    print 'Processed components for release %s is: %s' % (release_id, process_count)
    print 'Imported {0} contacts ({1} inherited)'.format(len(contacts), inherited)


path = r'./_test_data/package-owners-eae1399372a8'
import_package_owner(path)
