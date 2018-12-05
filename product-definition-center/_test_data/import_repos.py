#!/usr/bin/python

import os
import json
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rhpdc.settings")
django.setup()

from pdc.apps.release import models as release_models
from pdc.apps.repository import serializers
from pdc.apps.repository import models


def import_repos(release_id, mapping_file):
    data = json.load(open(mapping_file, "r"))
    repos = []
    for variant in data.keys():
        if variant in ("Everything", "Everything-optional", "Server-LoadBalancer"):
            continue
        for arch in data[variant]:
            for service in data[variant][arch]:
                if service == "cdn-product-id":
                    continue
                if service == "cdn":
                    svc_name = "pulp"
                else:
                    svc_name = service
                for repo_type, repo_name in data[variant][arch][service].iteritems():
                    if not repo_name:
                        continue
                    repo = {
                        "release_id": release_id,
                        "service": svc_name,
                        "variant_uid": variant,
                        "arch": arch,
                        "shadow": bool("shadow" in repo_type or (repo_name and "shadow" in repo_name)),
                    }

                    # content_category
                    if "debug" in repo_type:
                        repo["content_category"] = "debug"
                    elif "source" in repo_type:
                        repo["content_category"] = "source"
                    else:
                        repo["content_category"] = "binary"

                    # content_format
                    if "-iso" in repo_type:
                        repo["content_format"] = "iso"
                    elif "-kickstart" in repo_type:
                        repo["content_format"] = "kickstart"
                    else:
                        repo["content_format"] = "rpm"

                    if repo["content_format"] == "kickstart" and "-" in variant:
                        # addons, optional
                        # we want kickstarts only for base variants
                        continue

                    # repo_family
                    if "dist" in repo_type:
                        repo["repo_family"] = "dist"
                    elif "beta" in repo_type:
                        repo["repo_family"] = "beta"
                    elif "htb" in repo_type:
                        repo["repo_family"] = "htb"

                    if isinstance(repo_name, list):
                        repo_names = repo_name
                    else:
                        repo_names = [repo_name]

                    for i in repo_names:
                        add_repo = repo.copy()
                        add_repo["name"] = i
                        # NOTE: skip existed repo
                        try:
                            serializer = serializers.RepoSerializer(data=add_repo)
                            # It is not expected the data could be invalid. If
                            # it is, raise an exception to abort the import.
                            serializer.is_valid(raise_exception=True)
                            attrs = serializer.validated_data
                            models.Repo.objects.get(
                                variant_arch=attrs["variant_arch"],
                                service=attrs["service"],
                                repo_family=attrs["repo_family"],
                                content_format=attrs["content_format"],
                                content_category=attrs["content_category"],
                                name=attrs["name"],
                                shadow=attrs["shadow"]
                            )
                        except models.Repo.DoesNotExist, release_models.VariantArch.DoesNotExist:
                            repos.append(add_repo)

    if repos:
        serializer = serializers.RepoSerializer(data=repos, many=True)
        if not serializer.is_valid():
            print serializer.errors
        else:
            serializer.save()

import_repos("rhel-7.0", "_test_data/repos/rhel-7.0/repos.json")
import_repos("rhel-7.1", "_test_data/repos/rhel-7.1/repos.json")
import_repos("rhel-le-7.1", "_test_data/repos/rhel-le-7.1/repos.json")
import_repos("supp-7.0@rhel-7", "_test_data/repos/supp-rhel-7.0/repos.json")
import_repos("rhscl-1.2@rhel-6", "_test_data/repos/rhscl-1.2-rhel-6/repos.json")
import_repos("rhscl-1.2@rhel-7", "_test_data/repos/rhscl-1.2-rhel-7/repos.json")
import_repos("satellite-6.0.4@rhel-5", "_test_data/repos/satellite-6.0.4-rhel-5/repos.json")
import_repos("satellite-6.0.4@rhel-6", "_test_data/repos/satellite-6.0.4-rhel-6/repos.json")
import_repos("satellite-6.0.4@rhel-7", "_test_data/repos/satellite-6.0.4-rhel-7/repos.json")
