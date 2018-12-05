import logging
import os
import threading
import json
import django
import productmd
from productmd.rpms import Rpms

import kobo.rpmlib
# NOTE: uncomment this line if you want to update dist git repos.
# from lxml import html

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from pdc.apps.common import models as common_models
from pdc.apps.contact import models as contact_models
from pdc.apps.component import models as component_models
from pdc.apps.release import models as release_models
from pdc.apps.compose import models


logging.basicConfig(level=logging.WARNING,
                    filename='import_with_verify.log',
                    filemode='w')

component_count = 0


global_component_lock = threading.Lock()
release_component_lock = threading.Lock()

# Lock that used to protect the call against the dist git server
# NOTE: uncomment this line if you want to update cache_dist_git_repo.
# dist_server_lock = threading.Lock()
# DIST_GIT_CALL_DELAY = 2

# dist git repo branches dict:
# 'key' is repo name;
# 'value' is branch list;
repo_branches = {}

# load cached json file
with open('_test_data/cache_dist_git_repo_branches.json', 'r') as f:
    repo_branches = json.load(f)


def srpm_iterator(release_id, composeinfo, rpm_manifest):
    release_obj = release_models.Release.objects.get(release_id=release_id)

    ci = productmd.composeinfo.ComposeInfo()
    ci.deserialize(composeinfo)

    rm = Rpms()
    rm.deserialize(rpm_manifest)

    compose_date = "%s-%s-%s" % (ci.compose.date[:4], ci.compose.date[4:6], ci.compose.date[6:])
    compose_type = models.ComposeType.objects.get(name=ci.compose.type)
    compose_obj, _ = models.Compose.objects.get_or_create(
        release=release_obj,
        compose_id=ci.compose.id,
        compose_date=compose_date,
        compose_type=compose_type,
        compose_respin=ci.compose.respin,
        compose_label=ci.compose.label or None,
    )
    sources = set()
    for variant in ci.get_variants(recursive=True):
        variant_type = release_models.VariantType.objects.get(name=variant.type)
        variant_obj, created = models.Variant.objects.get_or_create(compose=compose_obj, variant_id=variant.id, variant_uid=variant.uid, variant_name=variant.name, variant_type=variant_type)

        for arch in variant.arches:
            arch_obj = common_models.Arch.objects.get(name=arch)
            var_arch_obj, created = models.VariantArch.objects.get_or_create(arch=arch_obj, variant=variant_obj)

            global component_count
            for srpm_nevra, rpms in rm.rpms.get(variant.uid, {}).get(arch, {}).iteritems():
                srpm_nvr = kobo.rpmlib.parse_nvra(srpm_nevra)  # noqa
                name = srpm_nvr.get('name', None)
                if name and name not in sources:
                    sources.add(name)
                    component_count += 1
                    yield release_obj, srpm_nevra, name
            for srpm_nevra, srpm_data in rm.rpms.get(variant.uid, {}).get("src", {}).iteritems():
                srpm_nvr = kobo.rpmlib.parse_nvra(srpm_nevra)  # noqa
                name = srpm_nvr.get('name', None)
                if name and name not in sources:
                    sources.add(name)
                    component_count += 1
                    yield release_obj, srpm_nevra, name


def import_with_verify_dist_git(release_id, composeinfo, rpm_manifest):
    for task_tuple in srpm_iterator(release_id, composeinfo, rpm_manifest):
        verify_url_gen_by_name(*task_tuple)


def verify_url_gen_by_name(release_obj, srpm_nevra, name):
    """
    There are three pattern we are using now:

    Same srpm_name with repo exists in dist git,
      try:
        # Pattern No.1: same release_component_name with global_component_name, with release branch.
        # e.g. MySQL-python in Release RHEL-7.1's spec file dist git url should be:
        # http://pkgs.devel.redhat.com/cgit/rpms/MySQL-python/tree/MySQL-python.spec?h=rhel-7.1
        <release_id> branch
      else:
        # Pattern No.2: same release_component_name with global_component_name, with layered branch.
        # e.g. ruby193 in Release RHSCL-1.2-RHEL-7's spec file dist git url should be:
        # http://pkgs.devel.redhat.com/cgit/rpms/ruby193/tree/ruby193.spec?h=rhscl-1.2-ruby193-rhel-7
        <short_release>-<name>-<base_product_id> branch
      else:
        # Pattern No.3: de-prefixed global_component_name, with layered_branch.
        # e.g. ruby193-rubygem-actionpack in Release RHSCL-1.2-RHEL-7's spec file dist git url should be:
        # http://pkgs.devel.redhat.com/cgit/rpms/rubygem-actionpack/tree/rubygem-actionpack.spec?h=rhscl-1.2-ruby193-rhel-7
      else:
        # uncovered case, not supported
    """
    branches = branches_in_dist_git(name)
    if branches:
        # Pattern No.1
        branch = release_obj.release_id
        layered_branch = ''
        if release_obj.base_product:
            short_release = '%s-%s' % (release_obj.short.lower(), release_obj.version)
            layered_branch = '%s-%s-%s' % (short_release, name, release_obj.base_product.base_product_id)
        if branch in branches:
            # if repo/branch exists, we take that repo name as GlobalComponent name;
            with global_component_lock:
                global_component, _ = component_models.GlobalComponent.objects.get_or_create(
                    name=name)
            # create/update release component
            create_or_update_release_component(release_obj,
                                               global_component,
                                               name,
                                               branch)
        elif layered_branch and layered_branch in branches:
            # if repo exists, we take that repo name as GlobalComponent name;
            with global_component_lock:
                global_component, _ = component_models.GlobalComponent.objects.get_or_create(
                    name=name)
            # create/update release component
            create_or_update_release_component(release_obj,
                                               global_component,
                                               name,
                                               layered_branch)
        elif name == 'devtoolset-3':
            # NOTE: Hack devtoolset-3 cases
            hacked_branch = 'devtoolset-3.1-rhel-7'
            if hacked_branch in branches:
                # if repo exists, we take that repo name as GlobalComponent name;
                with global_component_lock:
                    global_component, _ = component_models.GlobalComponent.objects.get_or_create(
                        name=name)
                # create/update release component
                create_or_update_release_component(release_obj,
                                                   global_component,
                                                   name,
                                                   hacked_branch)
        else:
            # try with prefix pattern
            verify_url_gen_with_prefix(release_obj, srpm_nevra, name, has_repo=True)
    else:
        verify_url_gen_with_prefix(release_obj, srpm_nevra, name, has_repo=False)


def verify_url_gen_with_prefix(release_obj, srpm_nevra, name, has_repo=False):
    """
    There are two pattern we are using now:
    De-prefixed repo name exists in dist git,
      try:
        # Pattern No.3: de-prefixed global_component_name, with layered_branch.
        # e.g. maven30-ant in Release RHSCL-1.2-RHEL-7's spec file dist git url should be:
        # http://pkgs.devel.redhat.com/cgit/rpms/ant/tree/ant.spec?h=rhscl-1.2-maven30-rhel-7
      else:
        # Pattern No.4: de-prefixed global_component_name, with prefixed_branch.
        # e.g.
        #
      else:
        # uncovered case, not supported
    """
    prefix = ''
    release_component_name = name
    for i in range(name.count('-')):
        cut_off, name = name.split('-', 1)
        temp_branches = branches_in_dist_git(name)
        if temp_branches:
            with global_component_lock:
                global_component, _ = component_models.GlobalComponent.objects.get_or_create(
                    name=name)

            prefix = release_component_name.split('-' + global_component.name)[0]
            if release_obj.base_product:
                # prefixed branch format: <release_component_prefix>-<base_product_id>
                prefixed_branch = '%s-%s' % (prefix, release_obj.base_product.base_product_id)
                short_release = '%s-%s' % (release_obj.short.lower(), release_obj.version)
                # layered branch format: <short_release_id>-<release_component_prefix>-<base_product_id>
                layered_branch = '%s-%s-%s' % (short_release, prefix, release_obj.base_product.base_product_id)
                # Pattern No.3
                if layered_branch in temp_branches:
                    # create/update release component
                    create_or_update_release_component(release_obj,
                                                       global_component,
                                                       release_component_name,
                                                       layered_branch)
                elif prefixed_branch in temp_branches:
                    # Pattern No.4
                    # create/update release component
                    create_or_update_release_component(release_obj,
                                                       global_component,
                                                       release_component_name,
                                                       prefixed_branch)
                elif prefixed_branch == 'devtoolset-3-rhel-7':
                    # NOTE: Hack devtoolset-3 cases
                    hacked_branch = 'devtoolset-3.1-rhel-7'
                    if hacked_branch in temp_branches:
                        # create/update release component
                        create_or_update_release_component(release_obj,
                                                           global_component,
                                                           release_component_name,
                                                           hacked_branch)
                else:
                    # uncovered case one:
                    msg_fmt = "Have de-prefixed repo, no layered_branch(%s) or prefixed_branch(%s) match"
                    logging.error("%s %s %s" % (release_component_name,
                                                srpm_nevra,
                                                msg_fmt % (layered_branch, prefixed_branch)))
            break
    if not prefix:
        # uncovered cases
        if has_repo:
            branch = release_obj.release_id
            layered_branch = ''
            if release_obj.base_product:
                short_release = '%s-%s' % (release_obj.short.lower(), release_obj.version)
                layered_branch = '%s-%s-%s' % (short_release,
                                               name,
                                               release_obj.base_product.base_product_id)
            if layered_branch:
                # uncovered case two:
                msg_fmt = "Have srpm name repo, no release_id(%s) nor layered_branch(%s) branch."
                logging.error("%s %s %s" % (release_component_name,
                                            srpm_nevra,
                                            msg_fmt % (branch, layered_branch)))
            else:
                # uncovered case three:
                msg_fmt = "Have srpm name repo, no release_id(%s) branch."
                logging.error("%s %s %s" % (release_component_name, srpm_nevra, msg_fmt % (branch)))
        else:
            # uncovered case four:
            logging.error("%s %s %s" % (release_component_name, srpm_nevra, "No repo found."))


def create_or_update_release_component(release_obj,
                                       global_component,
                                       name,
                                       dist_git_branch):
    with release_component_lock:
        try:
            # release component is already there
            release_component = component_models.ReleaseComponent.objects.get(
                release=release_obj,
                global_component=global_component,
                name=name)
        except component_models.ReleaseComponent.DoesNotExist:
            # release component is not there, need to be created
            release_component = component_models.ReleaseComponent.objects.create(
                release=release_obj,
                global_component=global_component,
                name=name,
                dist_git_branch=dist_git_branch)
            contacts = []
            for gcontact in contact_models.GlobalComponentContact.objects.filter(component=global_component):
                contacts.append(contact_models.ReleaseComponentContact(
                    component=release_component,
                    role=gcontact.role,
                    contact=gcontact.contact
                ))
            contact_models.ReleaseComponentContact.objects.bulk_create(contacts)
        else:
            # update dist_git_branch for release comonent
            release_component.dist_git_branch = dist_git_branch
            release_component.save()


def branches_in_dist_git(path):
    """
    Test if there is dist git repo with the given name;

    return all branches of repo in a list if the repo exists;
           [](empty list) if not;

    Get the branch list while testing if the repo exists,
    so we can use this list to verify branch instead of
    hitting the dist git server again.
    """
    if repo_branches and path in repo_branches:
        return repo_branches[path]
    else:
        # verify url against dist git server
        # NOTE: uncomment this section if you want to update
        #       cache dist git repos.
        # import requests
        # req_session = requests.Session()
        # url = "".join(['http://pkgs.devel.redhat.com/cgit/rpms/',
        #                path,
        #                '/refs/heads/'])
        # if dist_server_lock.acquire():
        #     response = req_session.get(url)
        #     time.sleep(DIST_GIT_CALL_DELAY)
        #     dist_server_lock.release()
        #     tree = html.fromstring(response.text)
        #     errors = tree.xpath('//div[@class="error"]/text()')
        #     if 'No repositories found' not in errors:
        #         return tree.xpath('//select[@name="h"]/option/text()')

        return []


if __name__ == "__main__":

    import_with_verify_dist_git("rhel-7.0",
                                json.load(open("_test_data/composes/rhel-7.0/composeinfo.json", "r")),
                                json.load(open("_test_data/composes/rhel-7.0/rpm-manifest.json", "r")))
    import_with_verify_dist_git("rhel-7.1",
                                json.load(open("_test_data/composes/rhel-7.1/composeinfo.json", "r")),
                                json.load(open("_test_data/composes/rhel-7.1/rpm-manifest.json", "r")))
    import_with_verify_dist_git("rhel-le-7.1",
                                json.load(open("_test_data/composes/rhel-le-7.1/composeinfo.json", "r")),
                                json.load(open("_test_data/composes/rhel-le-7.1/rpm-manifest.json", "r")))
    import_with_verify_dist_git("rhscl-1.2@rhel-7",
                                json.load(open("_test_data/composes/rhscl-1.2-rhel-7/composeinfo.json", "r")),
                                json.load(open("_test_data/composes/rhscl-1.2-rhel-7/rpm-manifest.json", "r")))

    # write cache file
    # NOTE: uncomment this section if you want to update cache
    #       dist git repos.
    # with open('_test_data/cache_dist_git_repo_branches.json', 'w') as f:
    #     json.dump(repo_branches, f)
