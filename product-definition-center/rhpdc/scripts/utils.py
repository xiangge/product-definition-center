import beanbag
import requests
import requests_kerberos
import warnings


def obtain_token(pdc):
    """
    Try to obtain token from all end-points that were ever used to serve the
    token. If the request returns 404 NOT FOUND, retry with older version of
    the URL.
    """
    token_end_points = ('token/obtain',
                        'obtain-token',
                        'obtain_token')
    for end_point in token_end_points:
        try:
            return pdc.auth[end_point]._()['token']
        except beanbag.BeanBagException, e:
            if e.response.status_code != 404:
                raise
    raise Exception('Could not obtain token from any known URL.')


def pdc_client(url, token, insecure, develop):
    """
    Because pdc_client is in upstream version and maybe change according to
    its own requirement, use some code here
    """
    session = requests.Session()

    if not develop:
        # For local environment, we don't need to require a token,
        # just access API directly.
        # REQUIRED, OPTIONAL, DISABLED
        session.auth = requests_kerberos.HTTPKerberosAuth(
            mutual_authentication=requests_kerberos.DISABLED)

    if insecure:
        # turn off for servers with insecure certificates
        session.verify = False

        # turn off warnings about making insecure calls
        if requests.__version__ < '2.4.0':
            print("Requests version is too old, please upgrade to 2.4.0 or latest.")
            # disable all warnings, it had better to upgrade requests.
            warnings.filterwarnings("ignore")
        else:
            requests.packages.urllib3.disable_warnings()

    pdc = beanbag.BeanBag(url, session=session)

    if not develop:
        # For develop environment, we don't need to require a token
        if not token:
            token = obtain_token(pdc)
        session.headers["Authorization"] = "Token %s" % token

    return pdc, session
