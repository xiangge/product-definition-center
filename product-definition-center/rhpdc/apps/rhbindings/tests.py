from rest_framework.test import APITestCase
from rest_framework import status
from django.core.urlresolvers import reverse

from pdc.apps.common.test_utils import TestCaseWithChangeSetMixin
from pdc.apps.release.models import Release
from pdc.apps.bindings.models import ReleaseBugzillaMapping
from .models import ReleaseBrewMapping, BrewTag, ProductPagesLink, Errata
from .serializers import ReleaseBrewMappingNestedSerializer


class ReleaseBrewMappingNestedSerializerTestCase(APITestCase):
    fixtures = [
        "rhpdc/apps/rhbindings/fixtures/tests/release.json",
    ]

    def setUp(self):
        self.release = Release.objects.get(release_id='rhel-7.0')

    def test_serialize(self):
        m = ReleaseBrewMapping.objects.create(release=self.release,
                                              default_target='default_target')
        m.allowed_tags.create(tag_name='tag')

        s = ReleaseBrewMappingNestedSerializer(instance=m)
        self.assertDictEqual(s.data, {'default_target': 'default_target',
                                      'allowed_tags': ['tag']})


class ReleaseRESTTestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        "rhpdc/apps/rhbindings/fixtures/tests/release.json",
        "rhpdc/apps/rhbindings/fixtures/tests/product.json",
        "rhpdc/apps/rhbindings/fixtures/tests/base_product.json",
        "rhpdc/apps/rhbindings/fixtures/tests/product_version.json",
    ]

    def test_create_with_complete_brew_and_bugzilla_mapping(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "bugzilla": {"product": "Fedora Bugzilla Product"},
                "brew": {"default_target": "f-20-candidate",
                         "allowed_tags": ["f-20-candidate-tag"]}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True, 'integrated_with': None, 'errata': None,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', "product_pages": None,
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(ReleaseBrewMapping.objects.count(), 1)
        self.assertNumChanges([3])

    def test_create_with_complete_brew_mapping(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "brew": {"default_target": "f-20-candidate",
                         "allowed_tags": ["f-20-candidate-tag"]}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', 'errata': None,
                     'bugzilla': None, 'integrated_with': None, "product_pages": None,
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(ReleaseBrewMapping.objects.count(), 1)
        self.assertNumChanges([2])

    def test_create_with_null_brew_content(self):
        url = reverse('release-list')
        response = self.client.get(url + '?brew_default_target=null')
        null_target_count = response.data['count']

        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "brew": None}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertNumChanges([1])
        url = reverse('release-list')
        response = self.client.get(url + '?brew_default_target=null')
        self.assertEqual(null_target_count + 1, response.data['count'])

    def test_create_with_brew_target(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "brew": {"default_target": "f-20-candidate"}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', 'errata': None,
                     'bugzilla': None, 'integrated_with': None, "product_pages": None,
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        args['brew']['allowed_tags'] = []
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(ReleaseBrewMapping.objects.count(), 1)
        self.assertNumChanges([2])

    def test_create_with_brew_tags(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "brew": {"allowed_tags": ["f-20-candidate"]}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', 'errata': None,
                     'bugzilla': None, 'integrated_with': None, 'product_pages': None,
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        args['brew']['default_target'] = None
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(ReleaseBrewMapping.objects.count(), 1)
        self.assertEqual(BrewTag.objects.count(), 1)
        self.assertNumChanges([2])

    def test_create_with_product_pages_link(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "product_pages": {"release_id": 15}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', 'brew': None, 'errata': None,
                     'bugzilla': None, 'integrated_with': None, 'product_pages': {'release_id': 15},
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(ProductPagesLink.objects.count(), 1)
        self.assertNumChanges([2])

    def test_create_with_errata_product_version(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "errata": {"product_version": "production_version_1"}}
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        args.update({"active": True,
                     'base_product': None, 'product_version': None, 'compose_set': [],
                     'dist_git': None, 'release_id': 'f-20', 'brew': None, 'product_pages': None,
                     'bugzilla': None, 'integrated_with': None, 'errata': {'product_version': "production_version_1"},
                     'sigkey': None, 'allowed_debuginfo_services': [],
                     'allowed_push_targets': [],
                     'allow_buildroot_push': False})
        self.assertDictEqual(dict(response.data), args)
        self.assertEqual(Errata.objects.count(), 1)
        self.assertNumChanges([2])

    def test_query_with_filter(self):
        url = reverse('release-list')
        response = self.client.get(url + '?brew_default_target=null')
        self.assertEqual(1, response.data['count'])
        response = self.client.get(url + '?brew_allowed_tag=rhel-7.0-candidate')
        self.assertEqual(0, response.data['count'])

    def test_query_with_filter_on_null_brew_target_with_no_brew_mapping(self):
        self.test_create_with_complete_brew_and_bugzilla_mapping()
        response = self.client.get(reverse('release-list'), {'brew_default_target': 'null'})
        self.assertEqual(1, response.data['count'])
        response = self.client.get(reverse('release-list'), {'brew_default_target': 'foo'})
        self.assertEqual(0, response.data['count'])

    def test_query_with_filter_on_null_brew_target_with_brew_mapping_without_target(self):
        self.test_create_with_complete_brew_and_bugzilla_mapping()
        response = self.client.get(reverse('release-list'), {'brew_default_target': 'null'})
        self.assertEqual(1, response.data['count'])
        response = self.client.get(reverse('release-list'), {'brew_default_target': 'missing'})
        self.assertEqual(0, response.data['count'])

    def test_query_with_product_pages_release_id(self):
        self.test_create_with_product_pages_link()
        response = self.client.get(reverse('release-list'), {'product_pages_release_id': 15})
        self.assertEqual(1, response.data['count'])
        response = self.client.get(reverse('release-list'), {'product_pages_release_id': 99})
        self.assertEqual(0, response.data['count'])

    def test_query_with_product_pages_non_numeric(self):
        response = self.client.get(reverse('release-list'), {'product_pages_release_id': 'hello'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_with_errata_product_version(self):
        self.test_create_with_errata_product_version()
        response = self.client.get(reverse('release-list'), {'errata_product_version': 'production_version_1'})
        self.assertEqual(1, response.data['count'])
        response = self.client.get(reverse('release-list'), {'errata_product_version': 'production_version_2'})
        self.assertEqual(0, response.data['count'])

    def test_filter_with_multi_brew_tags(self):
        args = {"name": "Fedora", "short": "f", "version": '20', "release_type": "ga",
                "brew": {"allowed_tags": ["f-20-candidate"]}}
        self.client.post(reverse('release-list'), args, format="json")
        args = {"name": "AwesomeProduct", "short": "a", "version": '7', "release_type": "ga",
                "brew": {"allowed_tags": ["a-7"]}}
        self.client.post(reverse('release-list'), args, format="json")
        response = self.client.get(reverse('release-list') + '?brew_allowed_tag=f-20-candidate&brew_allowed_tag=a-7')
        self.assertEqual(response.data['count'], 2)


class ReleaseCloneTestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        "rhpdc/apps/rhbindings/fixtures/tests/release.json",
        "rhpdc/apps/rhbindings/fixtures/tests/variant.json",
        "rhpdc/apps/rhbindings/fixtures/tests/variant_arch.json",
    ]

    def test_clone_create_brew_mapping(self):
        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'brew': {'default_target': 'rhel-7.1-candidate',
                                              'allowed_tags': ['tag1', 'tag2']}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('brew').get('default_target'), 'rhel-7.1-candidate')
        self.assertEqual(sorted(response.data.get('brew').get('allowed_tags')), sorted(['tag1', 'tag2']))
        self.assertEqual(1, ReleaseBrewMapping.objects.count())
        self.assertNumChanges([4])

    def test_clone_create_product_pages_link(self):
        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'product_pages': {'release_id': 11}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('product_pages'), {'release_id': 11})
        self.assertEqual(1, ProductPagesLink.objects.count())
        self.assertNumChanges([4])

    def test_clone_create_errata(self):
        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'errata': {'product_version': "production_version_1"}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('errata'), {'product_version': "production_version_1"})
        self.assertEqual(1, Errata.objects.count())
        self.assertNumChanges([4])

    def test_clone_old_brew(self):
        rbm = ReleaseBrewMapping.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            default_target='rhel-7.0-candidate'
        )
        rbm.allowed_tags.create(tag_name='tag1')
        rbm.allowed_tags.create(tag_name='tag2')

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('brew'),
                         {'default_target': 'rhel-7.0-candidate',
                          'allowed_tags': ['tag1', 'tag2']})
        self.assertEqual(2, ReleaseBrewMapping.objects.count())
        self.assertEqual(4, BrewTag.objects.count())
        self.assertNumChanges([4])

    def test_clone_old_product_pages_link(self):
        ProductPagesLink.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            product_pages_id=12
        )

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('product_pages'), {'release_id': 12})
        self.assertEqual(2, ProductPagesLink.objects.count())
        self.assertNumChanges([4])

    def test_clone_old_errata(self):
        Errata.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            product_version='production_version_1'
        )

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('errata'), {'product_version': 'production_version_1'})
        self.assertEqual(2, Errata.objects.count())
        self.assertNumChanges([4])

    def test_clone_remove_brew_mapping(self):
        rbm = ReleaseBrewMapping.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            default_target='rhel-7.0-candidate'
        )
        rbm.allowed_tags.create(tag_name='tag1')
        rbm.allowed_tags.create(tag_name='tag2')

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'brew': {}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('brew'), None)
        self.assertEqual(1, ReleaseBrewMapping.objects.count())
        self.assertEqual(ReleaseBrewMapping.objects.filter(release__release_id='rhel-7.1').count(), 0)
        self.assertEqual(2, BrewTag.objects.count())
        self.assertNumChanges([3])

    def test_clone_remove_product_pages_link(self):
        ProductPagesLink.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            product_pages_id=12
        )

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'product_pages': None},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('product_pages'), None)
        self.assertEqual(1, ProductPagesLink.objects.count())
        self.assertEqual(ProductPagesLink.objects.filter(release__release_id='rhel-7.1').count(), 0)
        self.assertNumChanges([3])

    def test_clone_remove_errata(self):
        Errata.objects.create(
            release=Release.objects.get(release_id='rhel-7.0'),
            product_version='production_version_1'
        )

        response = self.client.post(reverse('releaseclone-list'),
                                    {'old_release_id': 'rhel-7.0', 'version': '7.1',
                                     'errata': None},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('errata'), None)
        self.assertEqual(1, Errata.objects.count())
        self.assertEqual(Errata.objects.filter(release__release_id='rhel-7.1').count(), 0)
        self.assertNumChanges([3])


class ReleaseUpdateRESTTestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        'rhpdc/apps/rhbindings/fixtures/tests/release.json',
    ]

    def setUp(self):
        self.url = reverse('release-detail', args=['rhel-7.0'])
        self.release = Release.objects.get(release_id='rhel-7.0')
        self.serialized_release = {
            'short': 'rhel',
            'version': '7.0',
            'name': 'Red Hat Enterprise Linux',
            'active': True,
            'dist_git': None,
            'release_type': 'ga',
            'product_pages': None
        }

    def test_add_brew_mapping_complete(self):
        response = self.client.patch(self.url,
                                     {'brew': {'default_target': 'tgt', 'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brew'), {'default_target': 'tgt', 'allowed_tags': ['tag1']})
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertEqual(rbm.default_target, 'tgt')
        self.assertItemsEqual([tag.tag_name for tag in rbm.allowed_tags.all()],
                              ['tag1'])
        self.assertNumChanges([1])

    def test_update_brew_default_target(self):
        response = self.client.patch(self.url,
                                     {'brew': {'default_target': 'tgt'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brew'].get('default_target'), 'tgt')
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertEqual(rbm.default_target, 'tgt')
        self.assertNumChanges([1])

    def test_update_null_brew_content(self):
        response = self.client.patch(self.url,
                                     {'brew': {'default_target': 'tgt', 'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        url = reverse('release-list')
        response = self.client.get(url + '?brew_default_target=null')
        self.assertEqual(response.data['count'], 0)
        # clear brew mapping
        response = self.client.patch(self.url, {'brew': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(url + '?brew_default_target=null')
        self.assertEqual(response.data['count'], 1)

    def test_update_brew_allowed_tags(self):
        response = self.client.patch(self.url,
                                     {'brew': {'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brew'].get('allowed_tags'), ['tag1'])
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertItemsEqual([tag.tag_name for tag in rbm.allowed_tags.all()],
                              ['tag1'])
        self.assertNumChanges([1])

    def test_update_add_product_pages_link(self):
        response = self.client.patch(self.url,
                                     {'product_pages': {'release_id': 19}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('product_pages'), {'release_id': 19})
        self.assertEqual(ProductPagesLink.objects.get(release__release_id='rhel-7.0').product_pages_id, 19)
        self.assertNumChanges([1])

    def test_update_add_errata(self):
        response = self.client.patch(self.url,
                                     {'errata': {'product_version': 'production_version_1'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('errata'), {'product_version': 'production_version_1'})
        self.assertEqual(Errata.objects.get(release__release_id='rhel-7.0').product_version, 'production_version_1')
        self.assertNumChanges([1])

    def test_update_brew_default_target_on_existing_mapping(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='tgt')
        rbm.allowed_tags.create(tag_name='tag1')
        response = self.client.patch(self.url,
                                     {'brew': {'default_target': 'new tgt'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brew'].get('default_target'), 'new tgt')
        self.assertItemsEqual(response.data['brew'].get('allowed_tags'), ['tag1'])
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertNumChanges([1])

    def test_update_brew_allowed_tags_on_existing_mapping(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='tgt')
        rbm.allowed_tags.create(tag_name='tag1')
        response = self.client.patch(self.url,
                                     {'brew': {'allowed_tags': ['tag2']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data['brew'].get('allowed_tags'), ['tag2'])
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertItemsEqual([tag.tag_name for tag in rbm.allowed_tags.all()],
                              ['tag2'])
        self.assertNumChanges([1])

    def test_update_existing_product_pages_link(self):
        ProductPagesLink.objects.create(release=self.release, product_pages_id=16)
        response = self.client.patch(self.url,
                                     {'product_pages': {'release_id': 17}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product_pages'].get('release_id'), 17)
        self.assertEqual(ProductPagesLink.objects.get(release__release_id='rhel-7.0').product_pages_id, 17)
        self.assertNumChanges([1])

    def test_update_existing_errata(self):
        Errata.objects.create(release=self.release, product_version='production_version_1')
        response = self.client.patch(self.url,
                                     {'errata': {'product_version': 'production_version_2'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['errata'].get('product_version'), 'production_version_2')
        self.assertEqual(Errata.objects.get(release__release_id='rhel-7.0').product_version, 'production_version_2')
        self.assertNumChanges([1])

    def test_update_remove_brew_mapping(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='tgt')
        rbm.allowed_tags.create(tag_name='tag1')
        self.serialized_release['brew'] = None
        response = self.client.put(self.url, self.serialized_release, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brew'], None)
        response = self.client.get(reverse('release-detail', args=['rhel-7.0']))
        self.assertEqual(response.data['brew'], None)
        self.assertNumChanges([1])

    def test_update_remove_product_pages_link(self):
        ProductPagesLink.objects.create(release=self.release, product_pages_id=16)
        response = self.client.patch(self.url, {'product_pages': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ProductPagesLink.objects.count(), 0)
        self.assertNumChanges([1])

    def test_update_remove_errata(self):
        Errata.objects.create(release=self.release, product_version='production_version_1')
        self.assertEqual(Errata.objects.count(), 1)
        response = self.client.patch(self.url, {'errata': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Errata.objects.count(), 0)
        self.assertNumChanges([1])

    def test_missing_brew_mapping_should_remove_it(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='tgt')
        rbm.allowed_tags.create(tag_name='tag1')
        response = self.client.put(self.url, self.serialized_release, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['brew'])
        response = self.client.get(reverse('release-detail', args=['rhel-7.0']))
        self.assertIsNone(response.data['brew'])
        self.assertNumChanges([1])

    def test_update_missing_optional_fields_are_erased(self):
        args = {"release_type": "ga", "short": "f", "name": "Fedora", "version": "20", "base_product": None,
                "active": True, "brew": {"allowed_tags": ["tag1", "tag2"], "default_target": "f-20-candidate"},
                "errata": {"product_version": "f20"}, "product_pages": {"release_id": 1}
                }
        response = self.client.post(reverse('release-list'), args, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        url = reverse('release-detail', args=['f-20'])
        args = {"short": "f", "version": "20", "name": "Fedora",
                "active": True, "dist_git": None, "release_type": "ga"
                }
        response = self.client.put(url, args, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['brew'])
        self.assertIsNone(response.data['errata'])
        self.assertIsNone(response.data['product_pages'])
        self.assertNumChanges([4, 3])

    def test_remove_allowed_brew_tag(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag1')
        rbm.allowed_tags.create(tag_name='tag2')
        self.serialized_release['brew'] = {'allowed_tags': ['tag2', 'tag3']}
        response = self.client.put(self.url, self.serialized_release, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data['brew'].get('allowed_tags'), ['tag2', 'tag3'])
        rbm = ReleaseBrewMapping.objects.get(release__release_id='rhel-7.0')
        self.assertItemsEqual([tag.tag_name for tag in rbm.allowed_tags.all()],
                              ['tag2', 'tag3'])
        self.assertNumChanges([1])

    def test_patch_set_tags_with_null(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag1')
        response = self.client.patch(self.url, {'brew': {'allowed_tags': None}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])

    def test_patch_set_null_tag(self):
        response = self.client.patch(self.url, {'brew': {'allowed_tags': [None]}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])

    def test_patch_set_tags_to_current_status(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag1')
        response = self.client.patch(self.url,
                                     {'brew': {'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNumChanges([])

    def test_full_update_create_brew_mapping(self):
        response = self.client.put(reverse('release-detail', args=[self.release.release_id]),
                                   {'short': 'jihu-test',
                                    'version': '3.1',
                                    'release_type': 'ga',
                                    'name': 'update',
                                    'brew': {'allowed_tags': ['test']}},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('brew'), {'allowed_tags': ['test'],
                                                     'default_target': None})
        self.assertNumChanges([2])

    def test_updating_brew_default_target_does_not_delete_bugzilla_mapping(self):
        ReleaseBugzillaMapping.objects.create(release=self.release, bugzilla_product='Old product')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'default_target': 'default_tgt'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('bugzilla', {}).get('product'), 'Old product')
        self.assertNumChanges([1])

    def test_put_to_update_allowed_tags_erases_brew_default_target(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag1')
        self.serialized_release['brew'] = {'allowed_tags': ['tag2', 'tag3']}
        response = self.client.put(reverse('release-detail', args=[self.release.release_id]),
                                   self.serialized_release, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data.get('brew', {}).get('default_target'))
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'),
                              ['tag2', 'tag3'])

    def test_patch_to_set_allowed_tags(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'allowed_tags': ['tag1', 'tag2']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'),
                              ['tag1', 'tag2'])

    def test_patch_to_add_allowed_tags(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'add_allowed_tags': ['tag1', 'tag2']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'),
                              ['tag0', 'tag1', 'tag2'])

    def test_patch_to_add_allowed_tags_without_existing_mapping(self):
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'add_allowed_tags': ['tag1', 'tag2']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'),
                              ['tag1', 'tag2'])

    def test_patch_to_remove_allowed_tags(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'remove_allowed_tags': ['tag0']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'),
                              [])

    def test_patch_remove_allowed_tags_erases_mapping(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'remove_allowed_tags': ['tag0']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['brew'])

    def test_patch_to_remove_nonexisting_tag_fails(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'remove_allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_to_add_duplicate_tag_fails(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'add_allowed_tags': ['tag0']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('detail'),
                         ['Brew tag with this Brew mapping and Tag name already exists.'])

    def test_patch_to_add_and_remove_tags(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        rbm.allowed_tags.create(tag_name='tag0')
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'remove_allowed_tags': ['tag0'],
                                               'add_allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(response.data.get('brew', {}).get('allowed_tags'), ['tag1'])

    def test_patch_can_not_mix_add_with_set(self):
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'add_allowed_tags': ['tag0'],
                                               'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])

    def test_patch_can_not_mix_remove_with_set(self):
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'remove_allowed_tags': ['tag0'],
                                               'allowed_tags': ['tag1']}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])

    def test_remove_default_target_by_explicit_null(self):
        ReleaseBrewMapping.objects.create(release=self.release, default_target='target')
        response = self.client.put(reverse('release-detail', args=[self.release.release_id]),
                                   {'short': 'rhel',
                                    'name': 'Red Hat Enterprise Linux',
                                    'version': '7.0',
                                    'release_type': 'ga',
                                    'brew': {'default_target': None}},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brew'], None)

    def test_update_brew_with_wrong_field(self):
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     {'brew': {'foo': 'bar'}},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Unknown fields: "foo".'})
        self.assertNumChanges([])

    def test_put_with_add_allowed_tags(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag1')
        data = {}
        data.update(self.serialized_release)
        data['brew'] = {'add_allowed_tags': ['tag2']}
        response = self.client.put(reverse('release-detail', args=[self.release.release_id]),
                                   data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('add_allowed_tags/remove_allowed_tags', response.data['detail'][0])
        self.assertIn('partial', response.data['detail'][0])

    def test_remove_tags_when_invalid_dist_git(self):
        rbm = ReleaseBrewMapping.objects.create(release=self.release)
        rbm.allowed_tags.create(tag_name='tag1')
        data = {'dist_git': {'branch': None}, 'brew': {'remove_allowed_tags': ['tag1']}}
        response = self.client.patch(reverse('release-detail', args=[self.release.release_id]),
                                     data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNumChanges([])
        self.assertEqual(1, BrewTag.objects.all().count())


class ProductRESTTestCase(TestCaseWithChangeSetMixin, APITestCase):
    fixtures = [
        "rhpdc/apps/rhbindings/fixtures/tests/product.json"
    ]

    def test_create(self):
        args = {"name": "Fedora", "short": "f", "internal": 'False'}
        response = self.client.post(reverse('product-list'), args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data.get('internal'), False)
        self.assertNumChanges([2])

        args = {"name": "Fedora", "short": "ff", "internal": True}
        response = self.client.post(reverse('product-list'), args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data.get('internal'), True)
        self.assertNumChanges([2, 2])

        args = {"name": "Fedora", "short": "fff"}
        response = self.client.post(reverse('product-list'), args)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data.get('internal'), False)
        self.assertNumChanges([2, 2, 2])

    def test_patch_product_internal_status(self):
        args = {"name": "Fedora", "short": "f"}
        self.client.post(reverse('product-list'), args)
        response = self.client.patch(reverse('product-detail', args=['f']), {'internal': True}, format='json')
        self.assertEqual(response.data.get('internal'), True)

        response = self.client.patch(reverse('product-detail', args=['f']), {'internal': False}, format='json')
        self.assertEqual(response.data.get('internal'), False)
        self.assertNumChanges([2, 1, 1])

    def test_put_product_internal_status(self):
        args = {"name": "Fedora", "short": "f"}
        self.client.post(reverse('product-list'), args)
        response = self.client.put(reverse('product-detail', args=['f']),
                                   {'internal': True, 'name': "Fedora1", "short": "f"}, format='json')
        self.assertEqual(response.data.get('internal'), True)

        response = self.client.put(reverse('product-detail', args=['f']),
                                   {'internal': False, 'name': "Fedora1", "short": "f"}, format='json')
        self.assertEqual(response.data.get('internal'), False)
        self.assertNumChanges([2, 2, 1])

    def test_filter_product_with_internal_status(self):
        response = self.client.get(reverse('product-list'), data={'internal': False}, format='json')
        self.assertEqual(response.data['count'], 2)

        response = self.client.get(reverse('product-list'), data={'internal': True}, format='json')
        self.assertEqual(response.data['count'], 0)

        args = {"name": "Fedora", "short": "ff", "internal": True}
        self.client.post(reverse('product-list'), args)
        response = self.client.get(reverse('product-list'), data={'internal': True}, format='json')
        self.assertEqual(response.data['count'], 1)

    def test_filter_product_with_illegal_internal_status(self):
        response = self.client.get(reverse('product-list'), data={'internal': 'abcdee'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
