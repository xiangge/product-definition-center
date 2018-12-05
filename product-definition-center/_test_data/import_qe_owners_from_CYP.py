# -- coding: utf-8 -*-
import csv

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from django.db import transaction
from pdc.apps.contact.models import ContactRole, Person, Maillist, GlobalComponentContact
from pdc.apps.component.models import GlobalComponent
from pdc.apps.common import constants


def component_owner_reader(path):
    """
    Convert CSV file to data dict that ready to import;
    Will ignore these component with Owner 'NONE'.

    """
    with open(path, 'rt') as f:
        component_reader = csv.DictReader(f)

        for row in component_reader:
            if row.get('Owner name') is not "NONE":
                yield row


@transaction.atomic
def import_qe_owners_from_CYP(path):
    """
    Import QE owners data from CYP
    """
    group_contact_role, _ = ContactRole.objects.get_or_create(
        name=constants.QE_GROUP_CONTACT)
    leader_contact_role, _ = ContactRole.objects.get_or_create(
        name=constants.QE_LEADER_CONTACT)
    qe_ack_contact_role, _ = ContactRole.objects.get_or_create(
        name=constants.QE_ACK_CONTACT)

    process_count = 0

    contacts = []

    for component in component_owner_reader(path):
        global_component, _ = GlobalComponent.objects.get_or_create(
            name=component['component']
        )

        maillist, _ = Maillist.objects.get_or_create(
            mail_name=component['Owner name'],
            email=component['Owner email'].rstrip()
        )
        contacts.append(GlobalComponentContact(
            contact=maillist,
            role=group_contact_role,
            component=global_component
        ))

        person, _ = Person.objects.get_or_create(
            username=component['Lead E-mail'].split('@')[0],
            email=component['Lead E-mail']
        )
        contacts.append(GlobalComponentContact(
            component=global_component,
            role=leader_contact_role,
            contact=person
        ))
        contacts.append(GlobalComponentContact(
            contact=person,
            role=qe_ack_contact_role,
            component=global_component
        ))

        process_count += 1

    GlobalComponentContact.objects.bulk_create(contacts)

    print "%s components processed, %d contacts created." % (process_count, len(contacts))

path = r"./_test_data/CYP_components_20140821"
import_qe_owners_from_CYP(path)
