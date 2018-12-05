#! /usr/bin/env python

from __future__ import print_function

import os
import rpm
import sys
from multiprocessing import Pool
import threading
from beanbag import BeanBagException
from kobo.rpmlib import parse_nvra
from optparse import OptionParser
import logging
try:
    import json
except ImportError:
    import simplejson as json

import collections

from utils import pdc_client


class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


RPM_EXTENSION = ('.rpm', )
SRC_RPM_EXTENSION = ('.src.rpm', )
RPM_SOURCE_DIR = "/mnt/redhat/released"
BREW_ROOT_DIR = "/mnt/redhat/brewroot"
RPM_RESOURCE = 'rpms'
PROVIDES = 'provides'
REQUIRES = 'requires'
OBSOLETES = 'obsoletes'
CONFLICTS = 'conflicts'
RECOMMENDS = 'recommends'
SUGGESTS = 'suggests'
DEPENDENCY_TYPE_LIST = (PROVIDES, REQUIRES, OBSOLETES, CONFLICTS, RECOMMENDS, SUGGESTS)
BULK_NUM = 100
LOG_BATCH_NUM = BULK_NUM * 10
DEPENDENCY_TO_INT_DICT = {PROVIDES: 1,  # Dependency.PROVIDES,
                          REQUIRES: 2,  # Dependency.REQUIRES,
                          OBSOLETES: 3,  # Dependency.OBSOLETES,
                          CONFLICTS: 4,  # Dependency.CONFLICTS,
                          RECOMMENDS: 5,  # Dependency.RECOMMENDS,
                          SUGGESTS: 6  # Dependency.SUGGESTS
                          }

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
hdlr = logging.FileHandler(__file__ + '.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)


def is_qualified_file(filename):
    return filename.endswith(RPM_EXTENSION)


def collect_rpm_files_from_dir(dir_str, result):
    for root, sub_dirs, files in os.walk(dir_str):
        for filename in files:
            if is_qualified_file(filename):
                file_path = os.path.join(root, filename)
                result[filename] = file_path


def get_qualified_file_info(source_dir, checking_dir):
    source_dir_rpm_info = {}
    checking_dir_rpm_info = {}
    threads = []

    thread = threading.Thread(target=collect_rpm_files_from_dir, args=(source_dir, source_dir_rpm_info))
    thread.start()
    threads.append(thread)

    thread = threading.Thread(target=collect_rpm_files_from_dir, args=(checking_dir, checking_dir_rpm_info))
    thread.start()
    threads.append(thread)

    logger.info("Begin to collect RPMs information in %s and %s" % (source_dir, checking_dir))

    for thread in threads:
        thread.join()

    unqualified_rpm = set(source_dir_rpm_info.keys()) - set(checking_dir_rpm_info.keys())
    for key in unqualified_rpm:
        source_dir_rpm_info.pop(key)
    return source_dir_rpm_info


def rpm_is_src(hdr, file_path):
    # .src.rpm's hdr[rpm.RPMTAG_ARCH] may not be 'src'
    return file_path.endswith(SRC_RPM_EXTENSION) or hdr[rpm.RPMTAG_ARCH] == 'src'


def fill_rpm_basic_info(hdr, rpm_name, rpm_path, rpm_name_to_path_dict, is_src_rpm):
    # It will return like
    # {'src': False, 'name': 'patternfly1', 'epoch': '', 'version': '1.0.5', 'release': '4.el7eng', 'arch': 'noarch',
    # 'filename': gtk-vnc2-0.5.2-7.el7.x86_64.rpm}
    result = parse_nvra(hdr[rpm.RPMTAG_NEVRA])
    result['srpm_name'] = ''
    result['srpm_nevra'] = None
    result['filename'] = rpm_name
    if not result['epoch']:
        result['epoch'] = 0
    if rpm_is_src(hdr, rpm_path) or is_src_rpm:
        # srpm_nevra should be empty if and only if arch is src.
        result['srpm_name'] = result["name"]
        result['srpm_nevra'] = None
        result['src'] = True
        result['arch'] = 'src'
    else:
        # Get srpm information
        source_rpm = hdr[rpm.RPMTAG_SOURCERPM]
        if source_rpm in rpm_name_to_path_dict:
            # mark as src rpm to prevent dead loop
            srpm_info = parse_rpm(source_rpm, rpm_name_to_path_dict[source_rpm], rpm_name_to_path_dict, True)
            result['srpm_name'] = srpm_info["name"]
            result['srpm_nevra'] = "%s-%s:%s-%s.%s" % (srpm_info['name'], srpm_info['epoch'],
                                                       srpm_info['version'], srpm_info['release'], srpm_info['arch'])
    return result


def parse_rpm(rpm_name, rpm_path, rpm_name_to_path_dict, is_src_rpm=None):
    ts = rpm.ts()
    fdno = os.open(rpm_path, os.O_RDONLY)
    try:
        hdr = ts.hdrFromFdno(fdno)
    except rpm.error:
        os.close(fdno)
        fdno = os.open(rpm_path, os.O_RDONLY)
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
        hdr = ts.hdrFromFdno(fdno)
    finally:
        os.close(fdno)
    # It will return like
    # {'src': False, 'name': 'patternfly1', 'epoch': 0, 'version': '1.0.5', 'release': '4.el7eng', 'arch': 'noarch'}
    result = fill_rpm_basic_info(hdr, rpm_name, rpm_path, rpm_name_to_path_dict, is_src_rpm)
    # Dependencies
    result[REQUIRES] = hdr[rpm.RPMTAG_REQUIRENEVRS]
    result[PROVIDES] = hdr[rpm.RPMTAG_PROVIDENEVRS]
    result[OBSOLETES] = hdr[rpm.RPMTAG_OBSOLETENEVRS]
    result[CONFLICTS] = hdr[rpm.RPMTAG_CONFLICTNEVRS]
    result[RECOMMENDS] = hdr[rpm.RPMTAG_RECOMMENDNEVRS]
    result[SUGGESTS] = hdr[rpm.RPMTAG_SUGGESTNEVRS]
    return result


def rpm_exists(rpm_info, client):
    """ if exists, return id, or 0. The rpm for query parameters combination is unique if it exists."""
    data = {}
    for key in ('name', 'epoch', 'version', 'release', 'arch'):
        data[key] = rpm_info[key]
    response = client[RPM_RESOURCE]._(**data)
    if response['count']:
        return response['results'][0]['id']
    return False


def _generate_rpm_request_data(rpm_info, rpm_id=None):
    data = {'dependencies': {}}
    for key in DEPENDENCY_TYPE_LIST:
        if rpm_info[key]:
            # using OrderedSet to keep order or dependencies same as in rpm
            # ideall PDC wouldn't require unique deps: PDC-1085
            data['dependencies'][key] = list(OrderedSet(rpm_info[key]))
    # new rpm, post rpm basic info.
    if not rpm_id:
        for key in ('name', 'epoch', 'version', 'release', 'arch', 'srpm_name', 'srpm_nevra', 'filename'):
            data[key] = rpm_info[key]
    return data


child_client = None


def init_child_process():
    # this is used to initialize separate pdc connection for each save_or_update
    # call
    global child_client
    child_client, session = pdc_client(options.url, options.token, options.insecure, options.develop)


def save_or_update_rpm_and_dependency_info(rpm_info):
    result = False
    data = None

    try:
        client = child_client
        rpm_id = rpm_exists(rpm_info, client)
        data = _generate_rpm_request_data(rpm_info, rpm_id)

        if not rpm_id:
            # post
            client[RPM_RESOURCE]._(data)
        else:
            # patch
            client['%s/%d' % (RPM_RESOURCE, rpm_id)]._("PATCH", data)
        result = True
    except BeanBagException as e:
        print("%d %s" % (e.response.status_code, e.response.content))
        print("post data is: %s" % json.dumps(data))
    except Exception as e:
        print(str(e))
    return result


def insert_or_update_rpms(rpm_info_list, client):
    """ return (success count, failed count) """
    if not rpm_info_list:
        return 0, 0

    # First try to bulk insert
    request_data_list = [_generate_rpm_request_data(rpm_info) for rpm_info in rpm_info_list]
    try:
        logger.debug("Trying to insert %d rpms" % len(request_data_list))
        # Post
        client[RPM_RESOURCE]._(request_data_list)
        return len(request_data_list), 0
    except BeanBagException as e:
        logger.error("%d %s" % (e.response.status_code, e.response.content))
        logger.error("Bulk insert post data is: %s" % json.dumps(request_data_list))
    except Exception as e:
        logger.error(str(e))

    # Maybe some rpms already existed, insert or update one by one
    logger.debug("Inserting rpms one by one")
    failed_count = 0
    success_count = 0
    pool = Pool(processes=options.processes, initializer=init_child_process)

    ret = pool.map(save_or_update_rpm_and_dependency_info, rpm_info_list, 1)
    for r in ret:
        if r:
            success_count += 1
        else:
            failed_count += 1
    pool.close()
    pool.join()
    return success_count, failed_count


def parse_and_save_rpms(rpm_name_to_path_dict, client):
    success_count = 0
    failed_count = 0
    rpm_info_list = []
    for rpm_name, rpm_path in rpm_name_to_path_dict.iteritems():
        rpm_info_list.append(parse_rpm(rpm_name, rpm_path, rpm_name_to_path_dict))
        if len(rpm_info_list) % BULK_NUM == 0:
            success, failed = insert_or_update_rpms(rpm_info_list, client)
            rpm_info_list = []
            failed_count += failed
            success_count += success

            if (success_count + failed_count) % LOG_BATCH_NUM == 0:
                logger.info("Already saved %d RPMs' information.", success_count)
                logger.info("Failed count is %d", failed_count)
    success, failed = insert_or_update_rpms(rpm_info_list, client)
    failed_count += failed
    success_count += success

    logger.info("Totally saved or updated %d RPMs' information.", success_count)
    logger.info("Totally failed count is %d.", failed_count)


def main(source_dir, checking_dir, client):
    rpm_name_to_path_dict = get_qualified_file_info(source_dir, checking_dir)
    parse_and_save_rpms(rpm_name_to_path_dict, client)


if __name__ == '__main__':
    usage = """%prog -d <source directory> -c <directory to check rpm existence> -u {url}"""
    parser = OptionParser(usage)
    parser.add_option("-d", "--directory", help="the source directory", dest='source_dir',
                      default=RPM_SOURCE_DIR)
    parser.add_option("-c", "--check", help="directory to check the rpm existence", dest='checking_dir',
                      default=BREW_ROOT_DIR)
    parser.add_option("-v", "--develop", action="store_true", help="in development or not", dest='develop',
                      default=False)
    parser.add_option("-i", "--insecure", action="store_true", help="insecure", dest='insecure',
                      default=True)
    parser.add_option("-p", "--processes", help="number of parallel processes",
                      dest='processes', type='int', default=20)
    parser.add_option("-s", "--secure", action="store_false", help="secure", dest='insecure',
                      default=True)
    parser.add_option("-t", "--token", help="token", dest='token',
                      default=None)
    parser.add_option("-u", "--url", help="server url", dest='url',
                      default=None)

    options, args = parser.parse_args()

    if not os.path.isdir(options.source_dir):
        parser.error("Source directory doesn't exist")
    if not os.path.isdir(options.checking_dir):
        parser.error("Checking directory doesn't exist")
    if not options.url:
        parser.error("Must specify the server url.")

    client, session = pdc_client(options.url, options.token, options.insecure, options.develop)
    main(options.source_dir, options.checking_dir, client)
