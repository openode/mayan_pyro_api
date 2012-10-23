#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import Pyro4

from uuid import uuid4

try:
    from settings import *
except ImportError:
    HMAC_KEY = "d2d00896183011e28eb950e5493b2d90"
    DAEMON_NAME = "document_api"

    SERVER_IP = "192.168.23.7"
    NS_BCHOST = "mayan.coex.cz"

    # SERVER_IP = '192.168.23.68'
    # NS_BCHOST = "localhost"


################################################################################

Pyro4.config.HMAC_KEY = HMAC_KEY
Pyro4.config.HOST = SERVER_IP
Pyro4.config.NS_BCHOST = NS_BCHOST

################################################################################


class PlutoClient(object):
    """
        DocumentAPI client
    """

    def __init__(self):
        self.uri = "PYRONAME:%s@%s:9090" % (DAEMON_NAME, SERVER_IP)
        self.api = Pyro4.Proxy(self.uri)

    def retrive_thumbnails_wrapper(self, uuid, path):
        """
            wrapper for retrive document thumbnails
        """
        pages_count = self.api.get_page_count(uuid)
        for page in xrange(1, pages_count + 1):
            file_path = os.path.join(path, "%s_%s" % (uuid, page))
            img = self.api.retrive_thumbnails(uuid, page=page)
            f_loc = open(file_path, "w")
            f_loc.write(img)
            f_loc.close()

pluto_client = PlutoClient()

#######################################
# upload document example
#######################################

for f in ["tecna.xlsx", "Vypocet_RPSN.xlsx", "Seznam-prijemcu_28_3_2012.xlsx"]:

    print f

    status = pluto_client.api.upload_document(
        open("/home/martin/Dokumenty/testovaci_dokumenty/%s" % f, "r").read(),
        str(uuid4())
    )
    print status
    # >> {'document_id': 116, 'uuid': '47d6daa5-e2ef-4a17-be87-9c339d06120a', 'success': True}

    uuid = status["uuid"]
    # uuid = "ab98b14a-ade1-4340-931a-82b62a6bda9e"

    #######################################
    # retrive document thumbnail example
    #######################################

    files_path = "/tmp/pluto"
    pluto_client.retrive_thumbnails_wrapper(uuid, files_path)
    # >> store files to files_path

    #######################################
    # retrive text example
    #######################################

    print pluto_client.api.retrive_plaintext(uuid)
    # >> return document text reprezentation
