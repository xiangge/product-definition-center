from django.test import LiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException

import re


class RPMOverrideFormLiveTests(LiveServerTestCase):
    fixtures = [
        "pdc/apps/common/fixtures/test/sigkey.json",
        "pdc/apps/package/fixtures/test/rpm.json",
        "pdc/apps/release/fixtures/tests/release.json",
        "pdc/apps/compose/fixtures/tests/variant.json",
        "pdc/apps/compose/fixtures/tests/variant_arch.json",
        "pdc/apps/compose/fixtures/tests/compose_overriderpm.json",
        "pdc/apps/compose/fixtures/tests/compose.json",
        "pdc/apps/compose/fixtures/tests/compose_composerpm.json",
    ]

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(RPMOverrideFormLiveTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(RPMOverrideFormLiveTests, cls).tearDownClass()

    def _get_override_lines(self):
        result = []
        for row in self.gets_by_css('tbody tr'):
            parts = []
            for p in row.find_elements_by_css_selector('.form-control-static'):
                text = p.text
                try:
                    elem = p.find_element_by_tag_name('span')
                    text = re.search(r'glyphicon-(.+)', elem.get_attribute('class')).group(1)
                    text = {'minus': '-', 'plus': '+'}[text]
                except NoSuchElementException:
                    pass
                parts.append(text)
            result.append('.'.join(parts))
        return result

    def get_by_css(self, selector):
        """Shortcut for finding one element by CSS selector."""
        return self.selenium.find_element_by_css_selector(selector)

    def gets_by_css(self, selector):
        """Shortcut for finding many elements by CSS selector."""
        return self.selenium.find_elements_by_css_selector(selector)

    def test_page_has_required_elements(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.assertEqual(len(self.gets_by_css('input[type=checkbox]')), 2)
        self.assertEqual(len(self.gets_by_css('.form-row')), 3)

    def test_submit_clicked_checkbox(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.get_by_css('input[type=checkbox]').click()
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')

        self.assertEqual(self._get_override_lines(), ['Server.x86_64.bash.x86_64.-'])

    def test_submit_new_override(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.get_by_css('input[name^=news][name$=rpm_name]').send_keys('RPM_NAME')
        self.get_by_css('input[name^=news][name$=rpm_arch]').send_keys('RPM_ARCH')
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(self._get_override_lines(), ['Server.x86_64.RPM_NAME.RPM_ARCH.+'])

    def test_create_new_override(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))

        self.get_by_css('.variant-pair:first-of-type .add').click()

        self.assertEqual(len(self.gets_by_css('.variant-pair:first-of-type .form-row')), 2)

        names = self.gets_by_css('input[name^=news][name$=rpm_name]')
        archs = self.gets_by_css('input[name^=news][name$=rpm_arch]')
        for (idx, (nm, ar)) in enumerate(zip(names, archs)):
            nm.send_keys('RPM_NAME_' + str(idx))
            ar.send_keys('RPM_ARCH_' + str(idx))

        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(set(self._get_override_lines()),
                         set(['Server.x86_64.RPM_NAME_0.RPM_ARCH_0.+',
                              'Server.x86_64.RPM_NAME_1.RPM_ARCH_1.+']))

    def test_create_override_after_form_removal(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .add').click()
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .remove').click()

        self.get_by_css('input[name^=news][name$=rpm_name]').send_keys('RPM_NAME')
        self.get_by_css('input[name^=news][name$=rpm_arch]').send_keys('RPM_ARCH')
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(self._get_override_lines(), ['Server.x86_64.RPM_NAME.RPM_ARCH.+'])

    def test_can_add_fields_after_removing(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .add').click()
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .remove').click()
        self.assertIn('disabled', self.get_by_css('.variant-pair:first-of-type .remove').get_attribute('class'))
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .add').click()
        for _ in range(10):
            self.get_by_css('.variant-pair:first-of-type .remove').click()
        self.assertIn('disabled', self.get_by_css('.variant-pair:first-of-type .remove').get_attribute('class'))
        self.assertEqual(len(self.gets_by_css('.variant-pair:first-of-type .form-row')), 1)

    def test_fail_form_preserves_additional_override_fields(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.get_by_css('.variant-pair:first-of-type .add').click()
        names = self.gets_by_css('input[name^=news][name$=rpm_name]')
        for (idx, name) in enumerate(names):
            name.send_keys('RPM_NAME_' + str(idx))
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_form.html')
        num_forms = len(self.gets_by_css('.variant-pair:first-of-type .form-row'))
        self.assertEqual(num_forms, 2)
        self.assertEqual(self.get_by_css('.alert-danger').text,
                         'There are errors in the form.')
        num_err_rows = len(self.gets_by_css('.form-row.bg-danger'))
        self.assertEqual(num_err_rows, 2)

    def test_can_create_new_variant_with_overrides(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.get_by_css('.new-variant-pair input[name$=variant]').send_keys('Variant')
        self.get_by_css('.new-variant-pair input[name$=arch]').send_keys('Arch')
        self.get_by_css('.new-variant-pair .add').click()
        names = self.gets_by_css('.new-variant-pair input[name$=rpm_name]')
        archs = self.gets_by_css('.new-variant-pair input[name$=rpm_arch]')
        self.assertEqual(len(names), 2)
        self.assertEqual(len(archs), 2)
        for (idx, (name, arch)) in enumerate(zip(names, archs)):
            name.send_keys('RPM_NAME_' + str(idx))
            arch.send_keys('RPM_ARCH_' + str(idx))
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(set(self._get_override_lines()),
                         set(['Variant.Arch.RPM_NAME_0.RPM_ARCH_0.+',
                              'Variant.Arch.RPM_NAME_1.RPM_ARCH_1.+']))

    def test_can_create_more_variants_at_once(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        for x in range(3):
            elem = self.gets_by_css('.new-variant-pair')[-1]
            elem.find_element_by_css_selector('input[name$=variant]').send_keys('Variant' + str(x))
            elem.find_element_by_css_selector('input[name$=arch]').send_keys('Arch' + str(x))
            elem.find_element_by_css_selector('.add').click()
            names = elem.find_elements_by_css_selector('input[name$=rpm_name]')
            archs = elem.find_elements_by_css_selector('input[name$=rpm_arch]')
            self.assertEqual(len(names), 2)
            self.assertEqual(len(archs), 2)
            for (idx, (name, arch)) in enumerate(zip(names, archs)):
                name.send_keys('RPM_NAME_' + str(idx))
                arch.send_keys('RPM_ARCH_' + str(idx))
            self.get_by_css('.add-variant').click()
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(set(self._get_override_lines()),
                         set(['Variant0.Arch0.RPM_NAME_0.RPM_ARCH_0.+',
                              'Variant0.Arch0.RPM_NAME_1.RPM_ARCH_1.+',
                              'Variant1.Arch1.RPM_NAME_0.RPM_ARCH_0.+',
                              'Variant1.Arch1.RPM_NAME_1.RPM_ARCH_1.+',
                              'Variant2.Arch2.RPM_NAME_0.RPM_ARCH_0.+',
                              'Variant2.Arch2.RPM_NAME_1.RPM_ARCH_1.+']))

    def test_fail_form_preserves_additional_variant_fields(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        for x in range(3):
            elem = self.gets_by_css('.new-variant-pair')[x]
            elem.find_element_by_css_selector('input[name$=variant]').send_keys('Variant' + str(x))
            elem.find_element_by_css_selector('.add').click()
            names = elem.find_elements_by_css_selector('input[name$=rpm_name]')
            archs = elem.find_elements_by_css_selector('input[name$=rpm_arch]')
            self.assertEqual(len(names), 2)
            self.assertEqual(len(archs), 2)
            for (idx, (name, arch)) in enumerate(zip(names, archs)):
                name.send_keys('RPM_NAME_' + str(idx))
            self.get_by_css('.add-variant').click()
        self.get_by_css('[type=submit]').click()

        self.assertTemplateUsed('compose/override_form.html')
        self.assertEqual(self.get_by_css('.alert-danger').text,
                         'There are errors in the form.')
        num_err_rows = len(self.gets_by_css('.form-row.bg-danger'))
        self.assertEqual(num_err_rows, 9) # Three errors per variant

    def test_submit_preview_without_change(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        for box in self.gets_by_css('input[type=checkbox]'):
            box.click()
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.get_by_css('[type=submit]').click()
        boxes = self.gets_by_css('input[type=checkbox]')
        self.assertFalse(boxes[0].is_selected())
        self.assertTrue(boxes[1].is_selected())

    def test_preview_after_whole_cycle(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/override/manage/rhel-7.0/?package=bash'))
        self.gets_by_css('input[type=checkbox]')[0].click()
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.assertEqual(len(self.gets_by_css('tbody tr')), 1)
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_form.html')
        self.gets_by_css('input[type=checkbox]')[0].click()
        self.get_by_css('[type=submit]').click()
        self.assertTemplateUsed('compose/override_preview.html')
        self.get_by_css('[type=submit]').click()
        boxes = self.gets_by_css('input[type=checkbox]')
        self.assertTrue(boxes[0].is_selected())
        self.assertFalse(boxes[1].is_selected())
