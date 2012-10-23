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

    ###################################

    def ping(self):
        return "pong"

    ###################################

    def retrive_thumbnails(self, uuid, page):
        """
            @return: list of thumbnail's content of document's all pages
        """
        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            return []
        return open(document.get_image(page=page)).read()

    ###################################

    def retrive_plaintext(self, uuid, page=None):
        """
            @return: list of thumbnail's content of document's all pages
        """
        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            return ""

        content = []
        
        if page:
            pages_qs = document.pages.filter(page_number=page)
        else:
            pages_qs = document.pages.all()
         
        for page in pages_qs.iterator():
            if not page.content:
                continue
            content.append("\n%s" % page.content)
        return u''.join(content)

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
            "document_id": None,
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
            self.logger.error(str(e))
            # Don't leave the database in a broken state
            # document.delete()
            transaction.rollback()
            return status
        finally:
            output_descriptor.close()

        pages_count = document.pages.count()

        self.logger.info("Document created: %s" % repr({
            "uuid": uuid,
            "document": document.pk,
            "version": new_version.pk,
            "pages": pages_count,
            "size": self.get_file_size(tmp_path),
        }))

        # transform new document
        transformations, errors = SourceTransformation.transformations.get_for_object_as_list(document)
        new_version.apply_default_transformations(transformations)

        # remove temporary file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        status.update({
            "document_id": document.pk,
            "success": True,
            "uuid": document.uuid,
            "pages": pages_count,
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
