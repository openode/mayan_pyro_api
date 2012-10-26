# -*- coding: utf-8 -*-

import logging
import Pyro4

from django.core.management.base import NoArgsCommand

from pyro_api.settings import URI_PORT, URI_ID
from pyro_api.api import DocumentAPI

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
        daemon = Pyro4.Daemon(port=URI_PORT)
        # ns = Pyro4.locateNS()
        uri = daemon.register(DocumentAPI(), URI_ID)
        # ns.register(DAEMON_NAME, uri)
        logger.info("Connected to Pyro NameServer %s" % uri)
        daemon.requestLoop()
