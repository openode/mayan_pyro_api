# -*- coding: utf-8 -*-

import logging
import Pyro4
from time import sleep

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

    LOOP_LIMIT = 30

    def handle_noargs(self, *args, **kwargs):
        print "START COMMAND"

        from pyro_api.api import DocumentAPI

        i = 0

        daemon = None
        while i < self.LOOP_LIMIT:
            try:
                # try to connect to address (port/ip)
                daemon = Pyro4.Daemon(port=URI_PORT, host=SERVER_IP)
            except Exception, e:
                logger.error(str({
                    "error": e,
                    "loop": "%s/%s" % (i, self.LOOP_LIMIT)
                }))
                i += 1
                sleep(3)

            if daemon:
                break

        if not daemon:
            logger.critical("Pyro connection has not been created!")
            return

        # Pyro4.socketutil.setReuseAddr(daemon.sock)
        uri = daemon.register(DocumentAPI(), URI_ID)
        logger.info("Success connected to Pyro NameServer %s" % uri)
        try:
            daemon.requestLoop()
        finally:
            daemon.shutdown()
