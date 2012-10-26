# -*- coding: utf-8 -*-

import Pyro4

from pyro_api.settings import *

Pyro4.config.HMAC_KEY = HMAC_KEY
Pyro4.config.HOST = SERVER_IP
# Pyro4.config.NS_BCHOST = NS_BCHOST
