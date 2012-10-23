# -*- coding: utf-8 -*-

import logging
import Pyro4

from django.core.management.base import NoArgsCommand

from scheduler.runtime import scheduler
from pyro_api.settings import DAEMON_NAME
from pyro_api.api import DocumentAPI

################################################################################

scheduler.shutdown()
logger = logging.getLogger("api")

################################################################################


class Command(NoArgsCommand):
    """
        start API
    """
    def handle_noargs(self, *args, **kwargs):
        daemon = Pyro4.Daemon()
        ns = Pyro4.locateNS()
        uri = daemon.register(DocumentAPI())
        ns.register(DAEMON_NAME, uri)
        logger.info("Connected to Pyro NameServer %s" % uri)
        daemon.requestLoop()
