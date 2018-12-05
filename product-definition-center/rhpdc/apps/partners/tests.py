# -*- coding: utf-8 -*-
#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.urlresolvers import reverse

from pdc.apps.common.test_utils import TestCaseWithChangeSetMixin
from pdc.apps.release import models as release_models
from . import models


class PartnerTypeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        models.PartnerType.objects.create(name='customer')
        models.PartnerType.objects.create(name='partner')

    def test_can_list_partner_types(self):
        response = self.client.get(reverse('partnertype-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)


class PartnerAPITestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        "rhpdc/apps/partners/fixtures/tests/global_component.json",
    ]

    @classmethod
    def setUpTestData(cls):
        customer = models.PartnerType.objects.create(name='customer')
        models.PartnerType.objects.create(name='partner')

        models.Partner.objects.create(short='acme', name='ACME Corporation',
                                      type=customer)

    def test_create(self):
        data = {
            'short': 'jim',
            'name': 'Jim Inc.',
            'type': 'partner',
            'ftp_dir': 'ftp/dir',
            'rsync_dir': 'rsync/dir',
            'compose_arches': ['x86_64'],
            'errata_packages': ['python', 'java'],
        }
        response = self.client.post(reverse('partner-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['binary'] = True
        data['source'] = True
        data['enabled'] = True
        self.assertDictEqual(response.data, data)
        self.assertEqual(models.Partner.objects.count(), 2)
        self.assertNumChanges([1])

    def test_create_without_required_fields(self):
        response = self.client.post(reverse('partner-list'),
                                    {'short': 'jim', 'ftp_dir': 'ftp/dir', 'rsync_dir': 'rsync/dir'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.content)
        self.assertIn('type', response.content)
        self.assertEqual(models.Partner.objects.count(), 1)
        self.assertNumChanges([])

    def test_create_bad_type(self):
        response = self.client.post(reverse('partner-list'),
                                    {'short': 'jim', 'name': 'Jim Inc.', 'type': 'manager',
                                     'ftp_dir': 'ftp/dir', 'rsync_dir': 'rsync/dir'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer', response.content)
        self.assertIn('partner', response.content)
        self.assertEqual(models.Partner.objects.count(), 1)
        self.assertNumChanges([])

    def test_retrieve(self):
        response = self.client.get(reverse('partner-detail', args=['acme']))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            'short': 'acme',
            'name': 'ACME Corporation',
            'enabled': True,
            'binary': True,
            'source': True,
            'ftp_dir': '',
            'rsync_dir': '',
            'type': 'customer',
            'compose_arches': [],
            'errata_packages': [],
        }
        self.assertDictEqual(response.data, expected_data)

    def test_delete(self):
        response = self.client.delete(reverse('partner-detail', args=['acme']))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(models.Partner.objects.count(), 0)

    def test_partial_update(self):
        response = self.client.patch(reverse('partner-detail', args=['acme']),
                                     {'ftp_dir': '/somewhere/over/the/ftp'},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('ftp_dir'), '/somewhere/over/the/ftp')
        self.assertNumChanges([1])
        partner = models.Partner.objects.get(short='acme')
        self.assertEqual(partner.ftp_dir, '/somewhere/over/the/ftp')

    def test_update(self):
        data = {
            'short': 'acme',
            'name': 'ACME Inc.',
            'type': 'partner',
            'enabled': True,
            'binary': False,
            'source': False,
            'ftp_dir': 'ftp',
            'rsync_dir': 'rsync',
            'compose_arches': ['ppc64'],
            'errata_packages': ['python', 'java'],
        }
        response = self.client.put(reverse('partner-detail', args=['acme']),
                                   data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNumChanges([1])
        self.assertDictEqual(response.data, data)

    def test_update_short(self):
        response = self.client.patch(reverse('partner-detail', args=['acme']),
                                     {'short': 'emca'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('short'), 'emca')
        self.assertNumChanges([1])
        self.assertEqual(models.Partner.objects.filter(short='acme').count(), 0)
        self.assertEqual(models.Partner.objects.filter(short='emca').count(), 1)

    def test_update_missing_optional_fields_are_erased(self):
        data = {'short': 'acme', 'name': 'ACME Inc.', 'type': 'partner',
                'enabled': True, 'binary': False, 'source': False,
                'ftp_dir': 'ftp', 'rsync_dir': 'rsync'}
        response = self.client.put(reverse('partner-detail', args=['acme']),
                                   data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'short': 'acme', 'name': 'ACME Inc.', 'type': 'partner'}
        response = self.client.put(reverse('partner-detail', args=['acme']),
                                   data, format='json')
        self.assertEqual(response.data['enabled'], True)
        self.assertEqual(response.data['binary'], True)
        self.assertEqual(response.data['source'], True)
        self.assertEqual(response.data['ftp_dir'], '')
        self.assertEqual(response.data['rsync_dir'], '')
        self.assertEqual(response.data['compose_arches'], [])
        self.assertEqual(response.data['errata_packages'], [])
        self.assertNumChanges([1, 1])

    def test_filter_by_short(self):
        response = self.client.get(reverse('partner-list'), {'short': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_enabled(self):
        response = self.client.get(reverse('partner-list'), {'enabled': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_binary(self):
        response = self.client.get(reverse('partner-list'), {'binary': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_source(self):
        response = self.client.get(reverse('partner-list'), {'source': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_ftp_dir(self):
        response = self.client.get(reverse('partner-list'), {'ftp_dir': 'something'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_rsync_dir(self):
        response = self.client.get(reverse('partner-list'), {'rsync_dir': 'something'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_name(self):
        response = self.client.get(reverse('partner-list'), {'name': 'acme'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_filter_by_type(self):
        response = self.client.get(reverse('partner-list'), {'type': 'partner'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_multi_value(self):
        self.client.post(reverse('partner-list'),
                         {'short': 'jim', 'name': 'Jim Inc.', 'type': 'partner',
                          'ftp_dir': 'ftp/dir', 'rsync_dir': 'rsync/dir'},
                         format='json')
        self.client.post(reverse('partner-list'),
                         {'short': 'jim1', 'name': 'Jim1 Inc.', 'type': 'customer',
                          'ftp_dir': 'ftp/dir1', 'rsync_dir': 'rsync/dir1'},
                         format='json')
        response = self.client.get(reverse('partner-list') + '?ftp_dir=ftp/dir&ftp_dir=ftp/dir1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

    def test_filter_by_arch(self):
        data1 = {
            'short': 'jim',
            'name': 'Jim Inc.',
            'type': 'partner',
            'ftp_dir': 'ftp/dir',
            'rsync_dir': 'rsync/dir',
            'compose_arches': ['x86_64'],
        }
        data2 = {
            'short': 'jim1',
            'name': 'Jim1 Inc.',
            'type': 'partner',
            'ftp_dir': 'ftp/dir1',
            'rsync_dir': 'rsync/dir1',
            'compose_arches': ['x86_64', 'aarch64', 'ppc64le', 's390x'],
        }
        self.client.post(reverse('partner-list'), data1, format='json')
        self.client.post(reverse('partner-list'), data2, format='json')

        response = self.client.get(reverse('partner-list') + '?compose_arches=x86_64')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

        response = self.client.get(reverse('partner-list') + '?compose_arches=ppc64le')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        self.assertIn('ppc64le', response.data.get('results')[0]['compose_arches'])

        response = self.client.get(reverse('partner-list') + '?compose_arches=ppc64')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_errata_package(self):
        data1 = {
            'short': 'jim',
            'name': 'Jim Inc.',
            'type': 'partner',
            'ftp_dir': 'ftp/dir',
            'rsync_dir': 'rsync/dir',
            'errata_packages': ['python', 'java'],
        }
        data2 = {
            'short': 'jim1',
            'name': 'Jim1 Inc.',
            'type': 'partner',
            'ftp_dir': 'ftp/dir1',
            'rsync_dir': 'rsync/dir1',
            'errata_packages': ['python'],
        }
        self.client.post(reverse('partner-list'), data1, format='json')
        self.client.post(reverse('partner-list'), data2, format='json')

        response = self.client.get(reverse('partner-list') + '?errata_packages=python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

        response = self.client.get(reverse('partner-list') + '?errata_packages=java')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        self.assertIn('java', response.data.get('results')[0]['errata_packages'])

        response = self.client.get(reverse('partner-list') + '?errata_packages=MySQL-python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)


class PartnerMappingAPITestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        "rhpdc/apps/partners/fixtures/tests/variants_standalone.json",
    ]

    @classmethod
    def setUpTestData(cls):
        models.PartnerType.objects.create(name='customer')
        partner = models.PartnerType.objects.create(name='partner')

        p = models.Partner.objects.create(short='acme', name='ACME Corporation',
                                          type=partner)
        va = release_models.VariantArch.objects.get(pk=1)
        models.PartnerMapping.objects.create(partner=p, variant_arch=va)

    def test_create(self):
        response = self.client.post(reverse('partnermapping-list'),
                                    {'partner': 'acme',
                                     'variant_arch': {'release': 'release-1.0',
                                                      'variant': 'Client-UID',
                                                      'arch': 'x86_64'}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNumChanges([1])
        self.assertEqual(models.PartnerMapping.objects.count(), 2)

    def test_list(self):
        response = self.client.get(reverse('partnermapping-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_filter_by_partner(self):
        response = self.client.get(reverse('partnermapping-list'), {'partner': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_release(self):
        response = self.client.get(reverse('partnermapping-list'), {'release': 'release-1.1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_variant(self):
        response = self.client.get(reverse('partnermapping-list'), {'variant': 'Client-UID'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_by_arch(self):
        response = self.client.get(reverse('partnermapping-list'), {'variant': 'i386'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)

    def test_filter_multi_value(self):
        self.client.post(reverse('partnermapping-list'),
                         {'partner': 'acme',
                          'variant_arch': {'release': 'release-1.0',
                                           'variant': 'Client-UID',
                                           'arch': 'x86_64'}},
                         format='json')
        response = self.client.get(reverse('partnermapping-list') + '?variant=Server-UID&variant=Client-UID')
        self.assertEqual(response.data['count'], 2)

    def test_delete(self):
        url = reverse('partnermapping-detail', args=['acme/release-1.0/Server-UID/x86_64'])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNumChanges([1])
        self.assertEqual(models.PartnerMapping.objects.count(), 0)

    def test_create_with_variant_not_in_release(self):
        response = self.client.post(reverse('partnermapping-list'),
                                    {'partner': 'acme',
                                     'variant_arch': {'release': 'release-1.0',
                                                      'variant': 'Whatever',
                                                      'arch': 'x86_64'}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])
        self.assertEqual(models.PartnerMapping.objects.count(), 1)

    def test_create_with_non_existing_partner(self):
        response = self.client.post(reverse('partnermapping-list'),
                                    {'partner': 'foo',
                                     'variant_arch': {'release': 'release-1.0',
                                                      'variant': 'Server-UID',
                                                      'arch': 'x86_64'}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])
        self.assertEqual(models.PartnerMapping.objects.count(), 1)

    def test_create_duplicit(self):
        response = self.client.post(reverse('partnermapping-list'),
                                    {'partner': 'acme',
                                     'variant_arch': {'release': 'release-1.0',
                                                      'variant': 'Server-UID',
                                                      'arch': 'x86_64'}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])
        self.assertEqual(models.PartnerMapping.objects.count(), 1)
