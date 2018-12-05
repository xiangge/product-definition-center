#! /usr/bin/env python
import csv
import hashlib
import logging
import os
from optparse import OptionParser
import sys
import urllib2
import string
import subprocess
import StringIO

from beanbag import BeanBagException
from utils import pdc_client


CYP_URL = 'http://southpark.englab.brq.redhat.com:8083/export/'
SEP = '\r\n'
ROW_NUMBER_INTERVAL = 200
CONTACT_RESOURCE = 'global-component-contacts'
COMPONENT_RESOURCE = 'global-components'
MAIL_LIST_RESOURCE = 'contacts/mailing-lists'
PERSON_RESOURCE = 'contacts/people'
DEPRECATED_MAIL_LIST_RESOURCE = 'maillists'
DEPRECATED_PERSON_RESOURCE = 'persons'
PDC_URL_POSTFIX = "/rest_api/v1/"
HTTPS_DEFAULT_PORT = 443


logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


def _create_if_no_global_component(component_name):
    """return created global component number"""
    data = {'name': component_name}
    try:
        client[COMPONENT_RESOURCE]._(data)
        return 1
    except BeanBagException as e:
        if e.response.status_code == 400:
            return 0
        raise


def _create_or_patch_mail_list(mail_list_resource, mail_name, email):
    """return created mail list number"""
    created_count = patched_count = 0
    data = {'mail_name': mail_name}
    response = client[mail_list_resource]._(**data)
    data['email'] = email
    if not response['count']:
        client[mail_list_resource]._(data)
        created_count += 1
    else:
        id = response['results'][0]['id']
        ori_email = response['results'][0]['email']
        if ori_email != email:
            # email for the mail_name changed, PATCH
            client[mail_list_resource][id]._("PATCH", data)
            patched_count += 1
    return created_count, patched_count


def _create_if_no_person(person_resource, email, username):
    """return created person number"""
    # username is unique
    data = {'username': username, 'email': email}
    try:
        client[person_resource]._(data)
        return 1
    except BeanBagException as e:
        if e.response.status_code == 400:
            return 0
        raise


def _create_or_patch_contact(component_name, role, contact_field_name, contact_field_value):
    created_count = patch_count = 0
    data = {'component': component_name, 'role': role}
    response = client[CONTACT_RESOURCE]._(**data)

    if response['count']:
        if response['results'][0]['contact'][contact_field_name] != contact_field_value:
            # PATCH, update the global component contact
            id = response['results'][0]['id']
            patch_data = {'contact': {contact_field_name: contact_field_value}}
            client[CONTACT_RESOURCE][id]._("PATCH", patch_data)
            patch_count += 1
    else:
        # Create
        create_data = {'component': component_name, 'role': role,
                       'contact': {contact_field_name: contact_field_value}}
        client[CONTACT_RESOURCE]._(create_data)
        created_count += 1
    return created_count, patch_count


def _create_or_patch_contact_for_one_component(component_name, mail_list_mail_name, person_username):
    create_for_mail_list, patch_for_mail_list = _create_or_patch_contact(component_name, 'QE_Group', 'mail_name',
                                                                         mail_list_mail_name)
    create_for_person_leader, patch_for_person_leader = _create_or_patch_contact(component_name, 'QE_Leader',
                                                                                 'username', person_username)
    create_for_person_ack, patch_for_person_ack = _create_or_patch_contact(component_name, 'QE_ACK',
                                                                           'username', person_username)

    return (create_for_mail_list + create_for_person_leader + create_for_person_ack,
            patch_for_mail_list + patch_for_person_leader + patch_for_person_ack)


def _get_str_checksum(in_str):
    m = hashlib.md5()
    m.update(in_str)
    return m.hexdigest()


def _content_is_changed(file_path, content):
    if os.path.exists(file_path):
        with open(file_path) as f:
            previous_content = f.read()
            return content != previous_content
    return True


def _get_resources():
    try:
        client[MAIL_LIST_RESOURCE]._()
        return MAIL_LIST_RESOURCE, PERSON_RESOURCE
    except BeanBagException as e:
        if e.response.status_code == 404:
            logger.info("Using deprecated mail list and person resources name.")
            return DEPRECATED_MAIL_LIST_RESOURCE, DEPRECATED_PERSON_RESOURCE
        raise


def main(checksum_file_path):
    content = None
    created_component_count = created_maillist_count = patched_maillist_count = 0
    created_person_count = created_contact_count = patched_contact_count = 0
    logger.info("Start syncing...")
    try:
        cyp_content = urllib2.urlopen(CYP_URL).read()
        logger.info("Got CYP content. Start checking and importing...")
        current_cyp_checksum = _get_str_checksum(cyp_content)
        if not _content_is_changed(checksum_file_path, current_cyp_checksum):
            logger.info("CYP content doesn't change according to file %s. Exiting...." % checksum_file_path)
            return
        mail_list_resource, person_resource = _get_resources()
        reader = csv.DictReader(StringIO.StringIO(cyp_content))
        i = 0
        for row in reader:
            component_name = string.strip(row['component'])
            mail_list_mail_name = string.strip(row['Owner name'])
            mail_list_email = string.strip(row['Owner email'].rstrip())
            person_email = string.strip(row['Lead E-mail'])
            person_username = person_email.split('@')[0]

            created_component_count += _create_if_no_global_component(component_name)
            created_count, patched_count = _create_or_patch_mail_list(mail_list_resource,
                                                                      mail_list_mail_name, mail_list_email)
            created_maillist_count += created_count
            patched_maillist_count += patched_count

            created_person_count += _create_if_no_person(person_resource, person_email, person_username)

            created_count, patched_count = _create_or_patch_contact_for_one_component(component_name,
                                                                                      mail_list_mail_name,
                                                                                      person_username)
            created_contact_count += created_count
            patched_contact_count += patched_count
            i += 1
            if i % ROW_NUMBER_INTERVAL == 0:
                logger.info("Processed %d rows of content." % i)
                logger.info("Created %d global component(s)." % created_component_count)
                logger.info("Created %d mail list record(s), updated %d mail list record(s)." %
                            (created_maillist_count, patched_maillist_count))
                logger.info("Created %d person record(s)." % created_person_count)
                logger.info("Created %d global component contact(s), updated %d." %
                            (created_contact_count, patched_contact_count))
        # Processing completed. Store this time's checksum
        if not os.path.exists(os.path.dirname(checksum_file_path)):
            os.makedirs(os.path.dirname(checksum_file_path))
        with open(checksum_file_path, 'w') as f:
            f.write(current_cyp_checksum)

    finally:
        if content:
            content.close()
    logger.info("Total processed %d rows of content." % i)
    logger.info("Total created %d global component(s)." % created_component_count)
    logger.info("Total created %d mail list record(s), updated %d mail list record(s)." %
                (created_maillist_count, patched_maillist_count))
    logger.info("Total created %d person record(s)." % created_person_count)
    logger.info("Total created %d global component contact(s), updated %d." %
                (created_contact_count, patched_contact_count))


def __preparation_if_in_pdc_server(options):
    if options.local:
        virtual_host_cmd = "httpd -S | grep httpd | grep %s | head -1 | awk '{print $2}'" % HTTPS_DEFAULT_PORT
        host_name = subprocess.Popen(virtual_host_cmd, shell=True, stdout=subprocess.PIPE).stdout.read().splitlines()[0]
        options.url = "https://" + host_name + PDC_URL_POSTFIX

        kinit_cmd = "kinit -k -t /etc/httpd/conf/httpd.keytab HTTP/%s@REDHAT.COM" % host_name
        if os.system(kinit_cmd) != 0:
            logger.error("Run kinit command failed in local PDC server: %s ." % kinit_cmd)
            raise Exception("kinit failed in local PDC server.")


if __name__ == '__main__':
    usage = """%prog -u {url}"""
    parser = OptionParser(usage)
    default_cache_file = '/tmp/' + os.path.splitext(__file__)[0] + '.cache'
    parser.add_option("-f", "--file",
                      help="File that stored last time cache CYP content checksum and will store this time's",
                      default=default_cache_file)
    parser.add_option("-v", "--develop", action="store_true", help="in development or not", dest='develop',
                      default=False)
    parser.add_option("-l", "--local", action="store_true",
                      help="run in a server which is also the PDC server this script will run against.",
                      dest='local', default=False)
    parser.add_option("-i", "--insecure", action="store_true", help="insecure", dest='insecure',
                      default=True)
    parser.add_option("-s", "--secure", action="store_false", help="secure", dest='insecure',
                      default=True)
    parser.add_option("-t", "--token", help="token", dest='token',
                      default=None)
    parser.add_option("-u", "--url", help="server url", dest='url',
                      default=None)

    options, args = parser.parse_args()
    __preparation_if_in_pdc_server(options)
    try:
        client, session = pdc_client(options.url, options.token, options.insecure, options.develop)
    except BeanBagException as e:
        print "%d %s" % (e.response.status_code, e.response.content)
    except Exception as e:
        print str(e)
    else:
        main(options.file)
