%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:           pdc-client-redhat
Version:        1.7.0
Release:        1%{?dist}
Summary:        Console client for interacting with Product Definition Center
Group:          Development/Libraries
License:        MIT
Source0:        redhat.json
Source1:        bindings.py
BuildArch:      noarch
BuildRequires:  python
BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python-requests-kerberos
Requires:       pdc-client 

%if 0%{?rhel} <= 6 || 0%{?centos} <=6
Requires:       python-setuptools
Requires:       python-argparse
%endif

%description
This package contains a console client for interacting with Product Definition
Center (PDC)

%prep
cp -p %SOURCE0 .
cp -p %SOURCE1 .

%build

%install
rm -rf %{buildroot}

# Install PDC client configuration file
mkdir -p %{buildroot}/%{_sysconfdir}/pdc.d
install -m 0644 -D -p redhat.json %{buildroot}%{_sysconfdir}/pdc.d/redhat.json

# Install plugins
mkdir -p %{buildroot}/%{_datadir}/pdc-client/plugins
install -m 0644 -D -p bindings.py %{buildroot}%{_datadir}/pdc-client/plugins/bindings.py

%files
%dir %{_datadir}/pdc-client
%dir %{_datadir}/pdc-client/plugins
%{_datadir}/pdc-client/plugins/*
%dir %{_sysconfdir}/pdc.d
%attr(755, root, root) %{_sysconfdir}/pdc.d/redhat.json

%changelog
* Tue Aug 15 2017 Lukas Holecek <lholecek@redhat.com> - 1.7.0-1
- Rename pdc-client-redhat spec file (lholecek@redhat.com)
- Remove executable flag from redhat.json file (lholecek@redhat.com)
- Replace pdc-client option "insecure" with "ssl-verify" (lholecek@redhat.com)
- Change "insecure" to false in config for prod and stage server
  (bliu@redhat.com)

* Mon Jul 24 2017 Lukas Holecek <lholecek@redhat.com> - 1.2.0-2
- Verify CA certificate for production and stage servers

* Wed Nov 2 2016 bliu <bliu@redhat.com> 1.1.0-3
- release a new version with 1.1.0-3

* Mon Aug 29 2016 bliu <bliu@redhat.com> 1.1.0-2
- release a new version with 1.1.0-2

* Tue Jul 05 2016 bliu <bliu@redhat.com> 1.0.0-2
- Move plugins outside of python_sitelib. (bliu@redhat.com)
- Allow specifying plugins in the config file. (chuzhang@redhat.com)
- Change configuration files for pdc-client. (bliu@redhat.com)
- Add field 'subvariant' to image sub-command. (ycheng@redhat.com)

* Fri Feb 26 2016 bliu <bliu@redhat.com> 0.9.0-1
- Add pdc client project page and PyPI release docomentation.
  (ycheng@redhat.com)
- Let pdc client handle pdc warning header (ycheng@redhat.com)
- Pypi setup (sochotnicky@redhat.com)
- Fix release component update logging type (sochotnicky@redhat.com)


* Thu Feb 25 2016 Bo Liu <bliu@redhat.com> 0.9.0-1
- new package built with tito

