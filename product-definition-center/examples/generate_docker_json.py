#
# Copyright (c) 2015-2017 Red Hat
# Licensed under The MIT License (MIT)
# http://opensource.org/licenses/MIT
#
"""
Create json from docker image to be imported to PDC

Arguments
    build NVR for example:
    generate_docker_json.py rhel-tools-docker-7.1-9


You can pipe output of this to curl to import to PDC. For example:
 python generate_docker_list.py rhel-tools-docker-7.1-9 | \
    curl -H "Content-Type: application/json" \
         -X POST \
         --data @-  \
         https://pdc.app.test.eng.nay.redhat.com/rest_api/v1/build-images/ \
         -k -H "Authorization: Token <token>"

"""

from __future__ import print_function
import sys
from xmlrpclib import MultiCall

import koji
import json
from pdc.apps.common.constants import ARCH_SRC


brew = koji.ClientSession('http://brewhub.devel.redhat.com/brewhub')

build = brew.getBuild(sys.argv[1])
export = {}
export['image_id'] = sys.argv[1]
export['image_format'] = 'docker'
export['rpms'] = []

task = brew.getTaskInfo(build['task_id'])
if task['method'] == 'indirectionimage':
    tr = brew.getTaskRequest(build['task_id'])
    res = brew.getTaskResult(int(tr[0]['base_image_task']))
    arch = brew.listArchives(build['id'])
    assert(len(arch) == 1)
    export['md5'] = arch[0]['checksum']
    multicall = MultiCall(brew)
    for r in res['rpmlist']:
        multicall.getRPM({'name': r['name'],
                          'version': r['version'],
                          'release': r['release'],
                          'arch': r['arch']
                          })
    rpms = multicall()
else:
    archs = brew.listArchives(build['id'])
    for archive in archs:
        if archive['type_name'] in ('ks', 'cfg', 'xml'):
            continue
        export['md5'] = archive['checksum']
        archive_id = archive.get('id')
        rpms = brew.listRPMs(imageID=archive_id)

# first need to collect srpm names and for that we need builds
multicall = MultiCall(brew)
for rpm in rpms:
    multicall.getBuild(rpm['build_id'])

buildInfos = multicall()

rpm_infos = {}
for buildInfo in buildInfos:
    ri = {}
    ri["srpm_name"] = buildInfo['package_name']
    ri["srpm_nevra"] = buildInfo['nvr']
    rpm_infos[buildInfo['id']] = ri

for rpm in rpms:
    r = {}
    ri = rpm_infos[rpm["build_id"]]
    r["name"] = rpm["name"]
    r["epoch"] = rpm["epoch"] or 0
    r["version"] = rpm["version"]
    r["release"] = rpm["release"]
    r["arch"] = rpm["arch"]
    r["srpm_name"] = ri["srpm_name"]
    if ARCH_SRC != rpm["arch"]:
        r["srpm_nevra"] = ri["srpm_nevra"]
    export['rpms'].append(r)

print(json.dumps(export))
