"""
This module provides a helper class for importers using the API. The provided
request is set up with a user with pdc.admin permissions.

When using this module, make sure to create a single request for as many API
calls as possible, otherwise the importing may become slow due to constant
creation of the user.
"""

from pdc.apps.common import test_utils


class ImportRequest(object):
    def __init__(self):
        self.changeset = test_utils.ChangesetMock()
        self._request = None
        self.user = test_utils.create_user('admin', perms=['pdc.admin'])
