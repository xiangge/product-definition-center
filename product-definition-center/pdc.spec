%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define srcname pdc
%define internal rhpdc
%define default_version 1.9.0
%define default_release 2
%{!?_release_: %define _release_ %{default_release}}
%define upstream product-definition-center-upstream

%{!?version: %define version %{default_version}}
%{!?release: %define release %{_release_}%{?dist}}

Name:           python-%{srcname}
Version:        %{version}
Release:        %{release}
Summary:        Red Hat Product Definition Center
Group:          Development/Libraries
License:        GPL
URL:            https://docs.engineering.redhat.com/display/HTD/PDC
Source0:        %{srcname}-%{version}-%{_release_}.tar.bz2
Source1:        %{upstream}.tar.gz
BuildArch:      noarch
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx
Requires:       python-requests
Requires:       python-requests-kerberos
Requires:       beanbag

%description
The Product Definition Center, at its core, is a database that defines every Red Hat products, and their relationships with several important entities.


%package -n %{srcname}-test-data
Summary: Product Definition Center test data
Requires: %{srcname}-server = %{version}-%{release}

%description -n %{srcname}-test-data
This package contains initial data (fixtures) for testing PDC functionality


%package -n %{srcname}-server
Summary: Product Definition Center (PDC) server part
Requires:       Django >= 1.8.1, Django < 1.9.0
Requires:       django-rest-framework >= 3.1, django-rest-framework < 3.3
Requires:       django-mptt >= 0.7.1
Requires:       kobo >= 0.4.2
Requires:       kobo-django
Requires:       kobo-rpmlib
Requires:       koji
Requires:       patternfly1 == 1.3.0
Requires:       productmd >= 1.1
Requires:       python-django-filter >= 0.9.2
Requires:       python-ldap
Requires:       python-markdown
Requires:       python-mock
Requires:       python-psycopg2
Requires:       python-requests
Requires:       python-requests-kerberos
Requires:       python-django-cors-headers
Requires:       python-stomppy
Requires:       python-django-rest-framework-composed-permissions

%description -n %{srcname}-server
This package contains server part of Product Definition Center (PDC)


%prep
%setup -q -n %{srcname}-%{version}-%{_release_}
%setup -q -T -D -a 1 -n %{srcname}-%{version}-%{_release_}

%build
make -C %{upstream}/docs/ html

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --root=%{buildroot}

# need to call setup.py for upstream
pushd %{upstream}
%{__python} setup.py install -O1 --root=%{buildroot}
popd

mkdir -p %{buildroot}/%{_datadir}/%{srcname}/static
mkdir -p %{buildroot}%{_defaultdocdir}/%{srcname}
mkdir -p %{buildroot}/%{python_sitelib}/%{internal}/_test_data
cp -R _test_data %{buildroot}/%{python_sitelib}/%{internal}
cp sync_to_psql.sh %{buildroot}/%{python_sitelib}/%{internal}
cp %{upstream}/pdc/settings_local.py.dist %{buildroot}/%{python_sitelib}/%{internal}
cp -R %{upstream}/docs %{buildroot}%{_defaultdocdir}/%{srcname}
cp manage.py %{buildroot}/%{python_sitelib}/%{internal}

install -m 0755 -D -p %{internal}/conf/pdc-sync-ldap.sample %{buildroot}%{_sysconfdir}/cron.daily/pdc-sync-ldap

# don't need egg info
for egg_info in $(find %{buildroot}/%{python_sitelib} -type d -name '*.egg-info'); do
  rm -rf $egg_info
done

# Install apache config for the app:
install -m 0644 -D -p %{upstream}/conf/pdc-httpd.conf.sample %{buildroot}%{_defaultdocdir}/pdc/pdc.conf.sample

# Install import CYP contacts script
install -m 0755 -D -p %{internal}/scripts/import_contacts_from_CYP.py %{buildroot}/usr/bin/import_contacts_from_CYP
install -m 0755 -D -p %{internal}/conf/import_contacts_from_CYP.sample %{buildroot}%{_sysconfdir}/cron.hourly/import_contacts_from_CYP

# Install pdc sync ldap script
install -m 0755 -D -p %{upstream}/pdc/pdc-sync-ldap %{buildroot}/usr/bin/pdc-sync-ldap


# only remove static dir when it's a uninstallation
# $1 == 0: uninstallation
# $1 == 1: upgrade
%preun
if [ "$1" = 0 ]; then
  rm -rf %{_datadir}/%{srcname}/static
fi


%files -n %{srcname}-server
%defattr(-,root,apache,-)
%{_defaultdocdir}/pdc
%{python_sitelib}/%{srcname}
%{python_sitelib}/contrib
%{python_sitelib}/%{internal}
%exclude %{python_sitelib}/%{internal}/conf
%exclude %{python_sitelib}/%{internal}/_test_data
%{_datadir}/%{srcname}
%attr(755, root, root) %{_sysconfdir}/cron.daily/pdc-sync-ldap
%attr(755, root, root) /usr/bin/pdc-sync-ldap

%files -n %{srcname}-test-data
%{python_sitelib}/%{internal}/_test_data
%attr(755, root, root) %{_bindir}/import_contacts_from_CYP
%attr(755, root, root) %{_sysconfdir}/cron.hourly/import_contacts_from_CYP

%changelog
* Wed Nov 15 2017 Chuang Cao <chcao@redhat.com> 1.9.0-2
- [rhpdc] Update link for bug reports (lholecek@redhat.com)
- [rhpdc] Add errata_packages field to partners API (lholecek@redhat.com)
- [rhpdc] Fix saving compose_arches in changelog (lholecek@redhat.com)
- [rhpdc] Add compose_arches field to partners API (lholecek@redhat.com)
- Fix checking arch for multi-destinations API (lholecek@redhat.com)

* Mon Nov 13 2017 Chuang Cao <chcao@redhat.com> 1.9.0-1
- Add release-files endpoint (chcao@redhat.com)
- Allow filter multi-destinations by repo names (lholecek@redhat.com)
- Fix filtering by subscribers for mutli-destinations (lholecek@redhat.com)
- Use numerical ID to refer to variant-cpes (lholecek@redhat.com)
- Fix filter type of IDs in docs (lholecek@redhat.com)
- Ignore files created by setuptools (lholecek@redhat.com)
- Support OneToOneRel in RelatedNestedOrderingFilter (chuzhang@redhat.com)
- Fix reporting some validation errors (lholecek@redhat.com)
- Remove "trailing slash" hint from errors (lholecek@redhat.com)
- Fix partial update of variant-cpes (lholecek@redhat.com)
- Fix flake8 warnings (lholecek@redhat.com)
- Restrict djangorestframework's version (chcao@redhat.com)
- Fix the URL format in the unreleasedvariants documentation
  (matthew.prahl@outlook.com)
- Remove unused 'lookup_regex' variable (matthew.prahl@outlook.com)
- Add a delete test for the unreleasedvariants API (matthew.prahl@outlook.com)
- Fix the PATCH API in unreleasedvariants (matthew.prahl@outlook.com)
- Filter multi-destinations by repo release_id (lholecek@redhat.com)
- Add multi-destinations (multi-product) endpoint (lholecek@redhat.com)

* Thu Oct 19 2017 Lukas Holecek <lholecek@redhat.com> 1.8.0-1
- [rhpdc] Move adjust-package-name Makefile macro to script (lholecek@redhat.com)
- [rhpdc] Import upstream settings from settings_common (chuzhang@redhat.com)
- [rhpdc] Modify test cases according to upstream api change (chuzhang@redhat.com)
- Add push-targets endpoint and allowed_push_targets fields
- Add allowed_debuginfos for release (chcao@redhat.com)
- Add allow_buildroot_push to release API (chuzhang@redhat.com)
- Add signing key in release api (chcao@redhat.com)
- Add cpes endpoint (lholecek@redhat.com)
- Add variant-cpes endpoint (lholecek@redhat.com)
- Add descending ordering documentation on API pages (lholecek@redhat.com)
- Add API documentation links (lholecek@redhat.com)
- Make ComponentBranch filters case-sensitive (matt_prahl@live.com)
- Move common settings in one file (chuzhang@redhat.com)
- Always allow to select fields to display (lholecek@redhat.com)
- Allow to use ordering names from serialized JSON (lholecek@redhat.com)
- Fix not-found error string (lholecek@redhat.com)
- Fix passing field errors to client (lholecek@redhat.com)
- Use fuzzy filter for resources (lholecek@redhat.com)
- Omit changing response for DEBUG mode (lholecek@redhat.com)
- Simplify enabling debug toolbar in settings (lholecek@redhat.com)
- doc: fix "then" spelling (kdreyer@redhat.com)

* Wed Aug 23 2017 Chuang Cao <chcao@redhat.com> 1.7.0-2
- Change the related upstream version from 1.2.0-1 to 1.7.0-1

* Mon Aug 14 2017 Chuang Cao <chcao@redhat.com> 1.7.0-1
- Build and install RPM with Jenkins
- Remove unused jsonfield
- Add python-django-jsonfield as a dependency
- Remove the MVP Info from title line
- Remove the None value in list
- Bump up copyright year
- Check errors in sync_to_psql.sh
- Fix CMD format in Dockerfile
- Use requirements from upstream
- Docker: modify development env setup
- Add the MVP on Red Hat PDC front page
- Revert "Add initial usage docs rendered in webui."
- Add initial usage docs rendered in webui
- Fix generating graphs for apps with a label
- Add tests for ordering
- Fix passing a serialization error to client
- Modify the comment of disable api permission
- Remove unneeded django-jsonfield dependency
- Add python-django-jsonfield as a dependency
- Remove duplicate string-to-bool conversion function
- Merge pull request #431 from fedora-modularity/modularity
- Flake8 fixes
- Update doc strings
- Remove unneeded parentheses
- Remove unused test_tree.json
- Remove all references to "tree" which we never ended up using
- Move the folder from tree/ to module/
- Allow filtering modules by RPM's srpm_commit_branch
- Add missing database migration script for srpm_commit_hash and
  srpm_commit_branch
- Allow storing RPMs used in module build
- Add filters for build_deps and runtime_deps
- Make flake8 happy
- Add an active boolean field and use variant_uid for the lookup_field
- Fix app loading in django 1.9 like in #419
- Get the repository test suite working again
- Get the release app test suite working again
- Also require django-jsonfield for devel and tests
- Add 'modulemd' field to unreleasedvariants
- New style deps for stream-based modulemd 1.0
- (Un)Serialize dependencies as simple strings
- fix RelatedManager not iterable by iterating over .all()
- Add exports for UnreleasedVariant *_deps
- add UnreleasedVariant *_deps to filters
- Don't require runtime_deps/build_deps in the API
- implement querying of variant runtime/build deps
- Add comment to variant_version/_release API docs
- Don't require variant_version/_release in the API
- Add variant_version/_release to release.Variant
- Add comment to variant_version/_release.
- add missing fields to test API calls
- API end points are plural, not singular
- sync up filters with changes in the models
- Add lookup_field etc. to Tree/UnreleasedVariant
- fix URLs in API docs
- add migrations for Tree and UnreleasedVariant
- rename TreeVariant* to UnreleasedVariant*
- require django-jsonfield
- move JSON test data to own file
- Add initial version of tree app into pdc
- Add release variant type 'module'
- Add nested ordering filter
- Add the component-branches, component-sla-types,
  component-branch-slas APIs
- Add .idea to .gitignore
- Allow to add/update/remove component relationship types
- Fix mapping volume in example docker command
- Fix installing kobo from requirements
- Fix accidentally uncommented line in default settings
- Default view of composes should be reversed in order
- Merge pull request #339 from nphilipp/master--brand
- Merge pull request #432 from ralphbean/django-19-404
- Merge pull request #371 from ralphbean/mod_auth_oidc
- Handle new page_not_found argument in django-1.9

* Mon Aug 08 2016 Yu Cheng <ycheng@redhat.com> 1.1.0-1
- Take keys into account for ordering for APIs with list function.
- Add a new API for resource permission control.
- Add cache control headers to PDC HTTP response.
- Support multiple dict values and empty input for /composes/{compose_id}/rpm-mapping/
- Support regexp search in rpm name.

* Mon May 09 2016 Yu Cheng <ycheng@redhat.com> 1.0.0-1
- Add a new API to copy rpm overrides from one release to another.
- Enable query with multiple values for same filter via REST
- Add internal product flag to mark product as internal and builds should never be published to public.
- Release rpm-mapping API could work for a release without compose.
- Disable eus/aus repo checks

* Thu Feb 25 2016 Yu Cheng <ycheng@redhat.com> 0.9.0-0.1.beta
- Drop deprecated end points
- Rename resource variant-types to release-variant-types
- Add compose image RTT tests APIs.
- Add optional "built-for-release" field in rpms resource
- Add support for regexp for contact searches by component name
- Provide a response header field name "pdc-warning"

* Fri Dec 4 2015 Yu Cheng <ycheng@redhat.com> 0.8.0-0.1.beta
- Provide ability to store additional information about compose-trees
- Add support for storing partner information
- Restructure pdc client command structure
- Support new contact API in new pdc client.
- Remove compose/package api.
- Improve performance of the web UI
- Add 'errata' key to release to show 'product_version'
- Allow rpm dependencies to be duplicated.

* Tue Oct 13 2015 Eric Huang <jiahuang@redhat.com> 0.7.0-0.1.beta
- Provide user-friendly interface to pdc client
- Storing information about autorebuilds in PDC
- Able to store and query dependency metadata between RPMS
- As a user I want to keep track of reasons for changes
- Create internal docker image and update devel env setup document
- Report error on create/update of read-only field

* Tue Sep 8 2015 Eric Huang <jiahuang@redhat.com> 0.6.0-0.1.beta
- Open sourcing PDC
- Improve PDC landing page
- Add support for release-component types
- As an RCM I want to track rpms in releases without composes
- Log *basic* information about importing releases/composes/images
- Auto doc generation
- Provide permissions of the user within current session
- Support relationships between release-components
- Enable connecting build-image(s) to releases
- Dockerization PDC development env for upstream version

* Mon Aug 17 2015 Simon Zhang <chuzhang@redhat.com> 0.5.1-0.2.beta
- Fix sync script after adding messaging

* Thu Aug 13 2015 Simon Zhang <chuzhang@redhat.com> 0.5.1-0.1.beta
- Add StompMessenger to support STOMP protocol
- Add support of multi-endpoints failover policy

* Thu Jul 16 2015 Eric Huang <jiahuang@redhat.com> 0.5.0-0.1.beta
- Release component arbitrary grouping
- As RTT I am able to mark composes as tested on per-architecture basis
- As a BA I want to keep track of PDC usage
- Create HTML/JS UI for contact modifications
- Add messages for changes in composes
- Add support for sending messages in generic way onto message buses
- Unbundle beanbag in PDC
- Order of releases/composes in the API
- Add a link from PDC release to Product Pages release
- Add product_id column into repos/ in web ui

* Tue Jun 02 2015 Eric Huang <jiahuang@redhat.com> 0.4.0-0.1.beta
- Migrate PDC to rest framework 3.1
- Migrate Django to 1.8
- New api to get rpm_mapping for all packages in compose
- Improve contact models
- Improve PDC client by adding document and manpage

* Fri Apr 24 2015 Eric Huang <jiahuang@redhat.com> 0.3.0-0.2.beta
- Update migrations for release, release_component, repo, linked_release.

* Thu Apr 23 2015 Eric Huang <jiahuang@redhat.com> 0.3.0-0.1.beta
- Get integrated layered products to release
- Bulk operations in REST APIs
- Track component versions in composes
- Store Engineering Products (ids)
- Mapping bugzilla products to releases
- Track bugzilla subcomponents as well as specific components
- Support loading data from a specific json file for pdc_client

* Fri Mar 13 2015 Eric Huang <jiahuang@redhat.com> 0.2.0-0.2.beta
- Main rpm package name refactor to pdc-server
- CLI client working with any PDC instance(pdc_client)
- Record what components are in specific docker base images
- Ability to query docker images containing specific components
- Find composes with an older version of a package
- Ability to connect releases with brew tags
- Track bugzilla components for release-components
- Populate rpm mappings for releases without composes
- Map a brew build to a release the build was made for
- Improve the performance issue for import rpms

* Thu Jan 29 2015 Eric Huang <jiahuang@redhat.com> 0.1.0-0.2.beta
- As a QE I need to be able to determine the composes where specific rpm NVR is included
- As a Dev|RCM|QE I want to assign and query labels to global components
- query point of contact from CLI
- Implement remaining API for RPM mapping from XMLRPC in REST
- Revisit anonymous access to PDC REST API
- Link PDC release to a bugzilla product
- Sync data source of dist-git repositories and branches
- As an RCM I want to be able to clone releases

* Wed Dec 17 2014 Eric Huang <jiahuang@redhat.com> 0.1.0-0.1.beta
- REST APIs for product, release, component and contact
