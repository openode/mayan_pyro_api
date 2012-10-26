# -*- coding: utf-8 -*-

SERVER_IP = "192.168.23.7"
HMAC_KEY = "d2d00896183011e28eb950e5493b2d90"
URI_ID = "24142d22-1f57-11e2-9012-50e5493b2d90"
URI_PORT = 33333

# DEPRECATED: only for using with NameServer

# DAEMON_NAME = "document_api"
# NS_BCHOST = "mayan.coex.cz"

try:
    from settings_local import *
except ImportError:
    pass
