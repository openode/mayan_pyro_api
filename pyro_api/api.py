# -*- coding: utf-8 -*-

import os
import tempfile
import logging

from django.core.files import File
from django.db import transaction
from django.contrib.auth.models import User

from documents.models import Document, RecentDocument
from sources.models import SourceTransformation

################################################################################
################################################################################


class DocumentAPI(object):
    """
        API for comunication with Mayan
    """

    def __init__(self):
        self.logger = logging.getLogger("api")
        self.files = {}

    ###################################

    def ping(self):
        return "pong"

    def clean_file(self, uuid, page):
        key = "%s_%s" % (uuid, page)
        self.files[key].flush()
        del self.files[key]
        self.logger.info("Clean file cache: %s" % (key))

    ###################################

    def retrive_thumbnails(self, uuid, page):
        """
            @return: list of thumbnail's content of document's all pages
        """

        key = "%s_%s" % (uuid, page)

        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            self.logger.info("Not found %s: %s" % (uuid, page))
            return None

        try:
            document.get_image_cache_name(page, document.latest_version.pk)
            img_path = document.get_image(page=page)

            self.files[key] = open(img_path)
            return self.files[key].read()

        except Exception, e:
            self.logger.error("Error [%s]: %s" % (type(e), str(e)))
            return None

    ###################################

    def retrive_plaintext(self, uuid, page=None, default=""):
        """
            @return: list of thumbnail's content of document's all pages
        """
        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            return default

        content = []

        if page:
            pages_qs = document.pages.filter(page_number=page)
        else:
            pages_qs = document.pages.all()

        for page in pages_qs.iterator():
            if not page.content:
                continue
            content.append("\n%s" % page.content)
        return u''.join(content) or default

    ###################################

    def get_page_count(self, uuid):
        """
            @return: pages count od document
        """
        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            return 0
        return document.pages.count()

    ###################################

    @transaction.commit_on_success
    def upload_document(self, document, uuid):

        status = {
            "success": False,
            "uuid": "",
        }

        # create temporary file
        # Transfer file over Pyro is maybe not best idea. Problems can be on large files..
        # If problems, change this method to some better, for example: rsync, scp.
        handle, tmp_path = tempfile.mkstemp()
        os.close(handle)
        output_descriptor = open(tmp_path, "w+")
        output_descriptor.write(document)

        # create document in DB
        document = Document.objects.create()
        document.uuid = uuid
        Document.objects.filter(pk=document.pk).update(uuid=uuid)

        # add document for all users
        for user in User.objects.iterator():
            RecentDocument.objects.add_document_for_user(user, document)

        # create document version (it create thumbnails, ...)
        try:
            new_version = document.new_version(
                file=File(output_descriptor, name=uuid)
            )
        except Exception, e:
            self.logger.error("%s: %s" % (type(e), str(e)))
            # Don't leave the database in a broken state
            # document.delete()
            transaction.rollback()
            output_descriptor.close()
            return status
        finally:
            output_descriptor.close()

        pages_count = document.pages.count()
        size = self.get_file_size(tmp_path)
        ret = {
            "uuid": document.uuid,
            "document": document.pk,
            "version": new_version.pk,
            "pages": pages_count,
            "size": size,
        }
        self.logger.info("Document created: %s" % repr(ret))

        # transform new document
        transformations, errors = SourceTransformation.transformations.get_for_object_as_list(document)
        new_version.apply_default_transformations(transformations)

        # remove temporary file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        status.update(ret)
        status.update({
            "success": True,
        })

        return status

    ###################################

    def get_file_size(self, path, format=True):
        size = os.path.getsize(path)
        if format:
            for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return "%3.1f%s" % (size, x)
                size /= 1024.0
        return size
