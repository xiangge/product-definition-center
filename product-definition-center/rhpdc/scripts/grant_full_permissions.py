import logging
import sys

from beanbag import BeanBagException
from optparse import OptionParser
from utils import pdc_client


SOURCE_PERMISSIONS_API = 'auth/resource-permissions'
GROUP_RESOURCE_PERMISSIONS_API = 'auth/group-resource-permissions'

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


def main(group, client):
    full_resource_permissions = client[SOURCE_PERMISSIONS_API]._(**{'page_size': -1})
    success_number = 0
    for resource_permission in full_resource_permissions:
        try:
            data = {'group': group, 'resource': resource_permission['resource'],
                    'permission': resource_permission['permission']}
            client[GROUP_RESOURCE_PERMISSIONS_API]._(data)
            logger.info("Added %s" % data)
            success_number += 1
        except BeanBagException as e:
            logger.error("%d %s" % (e.response.status_code, e.response.content))
            logger.error("post data is: %s" % data)
        except Exception as e:
            logger.error(str(e))
    logger.info('Grant %d resource permissions successfully to group %s, %d failed' %
                (success_number, group, len(full_resource_permissions) - success_number))


if __name__ == '__main__':
    usage = """%prog -g <group name> -u {url}"""
    parser = OptionParser(usage)
    parser.add_option("-g", "--group", help="the group name", dest='group', default=None)
    parser.add_option("-v", "--develop", action="store_true", help="in development or not", dest='develop',
                      default=False)
    parser.add_option("-i", "--insecure", action="store_true", help="insecure", dest='insecure',
                      default=True)
    parser.add_option("-s", "--secure", action="store_false", help="secure", dest='insecure',
                      default=True)
    parser.add_option("-t", "--token", help="token", dest='token',
                      default=None)
    parser.add_option("-u", "--url", help="PDC API root url", dest='url',
                      default=None)

    options, args = parser.parse_args()

    if not options.url:
        parser.error("Must specify the server url.")

    if not options.group:
        parser.error("Must specify the group.")

    client, session = pdc_client(options.url, options.token, options.insecure, options.develop)
    main(options.group, client)
