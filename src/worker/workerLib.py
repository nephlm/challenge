"""
Much smaller worker lib.  Probably should just be rolled into worker.py.
"""

import requests

def getMyIPAddress():
    """
    Returns the public facing IP address of localhost.  Depending on
    network engineering there may be no way to reach localhost by
    using this address, but it will certainly be where traffic from
    localhost will appear to originate.

    @returns: str -- external ip address of localhost
    """
    return requests.get('https://api.ipify.org').text

