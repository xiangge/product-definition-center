"""
This module implements hooks for the release plugin of PDC client. It adds
support for displaying details of internal bindings as well as
creating/updating releases with these fields.
"""


def release_info(release):
    """Print detail info about a release.

    This hook is called as part of `release info` call and should print some
    human readable argument.

    :param release: object received from the API
    """
    fmt = '{0:20} {1}'
    if release['brew']:
        print '\nBrew'
        print fmt.format('Default Target', release['brew']['default_target'] or '')
        print fmt.format('Allowed Tags', ', '.join(release['brew']['allowed_tags']))

    if release['product_pages']:
        print '\nProduct Pages'
        print fmt.format('Release ID', release['product_pages']['release_id'])

    if release['errata']:
        print '\nErrata Tool'
        print fmt.format('Product Version', release['errata']['product_version'])


def release_parser_setup(subcmd):
    """Add arguments to the parser."""
    subcmd.add_argument('--product-pages-release-id', type=int)
    subcmd.add_argument('--brew-default-target')
    subcmd.add_argument('--brew-allowed-tags',
                        help='Comma separated list of allowed tags')
    subcmd.add_argument('--errata-product-version')


def release_update_prepare(args, data):
    """Extract data from the parser.

    Given data from the argument parser, update the object that will be sent to
    the server.

    :param args: result of parsing arguments returned by argparse library
    :param data: dict to be updated
    """
    if args.product_pages_release_id is not None:
        data['product_pages'] = ({'release_id': args.product_pages_release_id}
                                 if args.product_pages_release_id else None)

    brew = {}
    if args.brew_default_target is not None:
        brew['default_target'] = args.brew_default_target or None
    if args.brew_allowed_tags is not None:
        brew['allowed_tags'] = (args.brew_allowed_tags.split(',')
                                if args.brew_allowed_tags else [])
    if brew:
        data['brew'] = brew

    if args.errata_product_version is not None:
        data['errata'] = ({'product_version': args.errata_product_version}
                          if args.errata_product_version else None)
