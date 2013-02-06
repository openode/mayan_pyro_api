# -*- coding: utf-8 -*-

import logging
import Pyro4

from django.core.management.base import NoArgsCommand

from pyro_api.settings import URI_PORT, URI_ID, HMAC_KEY, SERVER_IP

################################################################################

Pyro4.config.HMAC_KEY = HMAC_KEY

################################################################################

from scheduler.runtime import scheduler
scheduler.shutdown()
logger = logging.getLogger("api")

################################################################################


class Command(NoArgsCommand):
    """
        start API
    """
    def handle_noargs(self, *args, **kwargs):

        from pyro_api.api import DocumentAPI

        daemon = Pyro4.Daemon(port=URI_PORT, host=SERVER_IP)
        uri = daemon.register(DocumentAPI(), URI_ID)
        logger.info("Connected to Pyro NameServer %s" % uri)
        daemon.requestLoop()
