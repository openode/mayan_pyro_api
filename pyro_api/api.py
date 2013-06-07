# -*- coding: utf-8 -*-

from collections import Counter
import errno
from functools import wraps
import logging
import os
import signal
import tempfile

from django.core.files import File
from django.db import transaction
from django.contrib.auth.models import User

from ocr.models import DocumentQueue
from ocr.literals import DOCUMENTQUEUE_STATE_STOPPED, DOCUMENTQUEUE_STATE_ACTIVE

from converter.exceptions import UnknownFileFormat
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

    def get_thumbnail_path(self, uuid, page):
        # key = "%s_%s" % (uuid, page)

        try:
            document = Document.objects.get(uuid=uuid)
        except Document.DoesNotExist:
            self.logger.info("Not found %s: %s" % (uuid, page))
            return None

        try:
            document.get_image_cache_name(page, document.latest_version.pk)
            img_path = document.get_image(page=page)
            # self.logger.info(img_path)
            return img_path
            # self.files[key] = open(img_path)
            # return self.files[key].read()

        except UnknownFileFormat:
            pass

        except Exception, e:
            self.logger.error("Error [%s]: %s" % (type(e), str(e)))

        return None

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
        # fd, tmp_path = tempfile.mkstemp()
        # os.close(fd)
        size = None
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:

            tmp_file.write(document)

            # create document in DB
            document = Document.objects.create()
            document.uuid = uuid
            Document.objects.filter(pk=document.pk).update(uuid=uuid)

            # add document for all users
            for user in User.objects.iterator():
                RecentDocument.objects.add_document_for_user(user, document)

            # create document version (it create thumbnails, ...)
            try:
                f = File(tmp_file, name=uuid)
                # new_version = self._create_mayan_document(document, f)
                new_version = document.new_version(file=f)
                f.close()

            except Exception, e:
                self.logger.error("%s: %s" % (type(e), str(e)))
                # Don't leave the database in a broken state
                # document.delete()
                transaction.rollback()
                return status

        pages_count = document.pages.count()

        if os.path.exists(tmp_file.name):
            size = self.get_file_size(tmp_file.name)

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
            os.remove(tmp_file.name)
        except OSError:
            pass

        status.update(ret)
        status.update({
            "success": True,
        })

        return status

    ###################################
    # Queue
    ###################################

    def get_documents_in_queue(self):
        ret = []
        for dq in DocumentQueue.objects.all():

            queue = Counter()
            for d in dq.queuedocument_set.all():
                queue[d.get_state_display()] += 1

            ret.append({
                "state": dq.get_state_display(),
                "name": dq.name,
                "queue": dict(queue),
                "pk": dq.pk
            })
        return ret

    def clean_queue(self, pk):
        self.logger.info("Start manualy empty queue: %s" % repr({"pk": pk}))

        ret = {
            "error": None,
            "success": False
        }
        dq = None
        try:
            dq = DocumentQueue.objects.get(pk=pk)
            dq.state = DOCUMENTQUEUE_STATE_STOPPED
            dq.save()

            queue_documents = dq.queuedocument_set.all()
            self.logger.info(
                "Try to remove %s document from queue %s." % (queue_documents.count(), dq.name)
            )
            for queue_document in queue_documents:
                queue_document.delete()

            ret.update({
                "success": True
            })
        except Exception, e:
            ret.update({
                "error": e
            })
            self.logger.error("Error during manualy empty queue: %s" % repr(e))
        finally:
            dq.state = DOCUMENTQUEUE_STATE_ACTIVE
            dq.save()

        return ret

    ###################################

    def get_file_size(self, path, format=True):
        size = os.path.getsize(path)
        if format:
            for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return "%3.1f%s" % (size, x)
                size /= 1024.0
        return size
