# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
import os

from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from jobs.models import Job, HDXExportRegion, SavedFeatureSelection, PartnerExportRegion
from django.contrib import admin
from django.contrib.gis.admin import GeoModelAdmin
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
import validators
import requests


class ExportRun(models.Model):
    """
    Model for one execution of an Export - associated with a storage directory on filesystem.
    """
    id = models.AutoField(primary_key=True, editable=False)
    uid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    job = models.ForeignKey(Job, related_name='runs')
    user = models.ForeignKey(User, related_name="runs", default=0)

    status = models.CharField(
        blank=True, max_length=20,
        db_index=True, default=''
    )
    started_at = models.DateTimeField(default=timezone.now, editable=False)
    finished_at = models.DateTimeField(editable=False, null=True)

    class Meta:
        db_table = 'export_runs'
        ordering = ['created_at']

    def __str__(self):
        return '{0}'.format(self.uid)

    def export_formats(self):
        return self.job.export_formats

    @property
    def process_time(self):
        if self.started_at and self.finished_at:
            return "{:.1f}".format((self.finished_at - self.started_at).total_seconds()/60)
        return None

    @property
    def total_time(self):
        if  self.finished_at:
            return "{:.1f}".format((self.finished_at - self.created_at).total_seconds()/60)
        return None

    @property
    def elapsed_time(self):
        return (self.finished_at or timezone.now()) - self.started_at

    @property
    def size(self):
        return sum(map(
            lambda task: task.filesize_bytes or 0, self.tasks.all()))


class ExportTask(models.Model):
    """
    Model for one export format within one export run.
    """
    id = models.AutoField(primary_key=True, editable=False)
    uid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    run = models.ForeignKey(ExportRun, related_name='tasks')
    status = models.CharField(blank=True, max_length=20, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    started_at = models.DateTimeField(editable=False, null=True)
    finished_at = models.DateTimeField(editable=False, null=True)
    filesize_bytes = models.IntegerField(null=True)
    filenames = ArrayField(models.TextField(null=True),default=list)

    class Meta:
        db_table = 'export_tasks'
        ordering = ['created_at']

    def __str__(self):
        return 'ExportTask uid: {0}'.format(self.uid)

    def username(self):
        return self.run.user

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return "{:.1f}".format((self.finished_at - self.started_at).total_seconds()/60)
        return None

    @property
    def filesize_mb(self):
        if self.filesize_bytes:
            return "{:.1f}".format((self.filesize_bytes)*0.000001)
        return None

    @property
    def download_urls(self):
        def fdownload(fname):
            valid=validators.url(fname)
            if valid==True:
                download_url = fname
                absolute_download_url=download_url
                try :
                    value = download_url.split('/')
                    name=value[-1]
                    split_name=name.split('_')
                    download_name=f"{split_name[0]}_{split_name[-1]}"  # getting human redable name ignoring unique id
                    fname=download_name
                except:
                    fname=f"""{self.run.job.name}_{self.name}.zip"""
                try:
                    with open(os.path.join(settings.EXPORT_DOWNLOAD_ROOT, str(self.run.uid),f"{name}_size.txt")) as f :
                        size=f.readline()
                    filesize_bytes=int(size)
                except:
                    filesize_bytes=0

            else:
                try:
                    filesize_bytes = os.path.getsize(os.path.join(settings.EXPORT_DOWNLOAD_ROOT, str(self.run.uid), fname).encode('utf-8'))
                except Exception:
                    filesize_bytes = 0
                download_url = os.path.join(settings.EXPORT_MEDIA_ROOT,str(self.run.uid), fname)
                absolute_download_url=settings.HOSTNAME + download_url
            return {
                "filename":fname,
                "filesize_bytes": filesize_bytes,
                "download_url":download_url,
                "absolute_download_url":absolute_download_url
            }
        return map(fdownload, self.filenames)



class ExportRunAdmin(admin.ModelAdmin):

    def start(self, request, queryset):
        from tasks.task_runners import run_task_async_ondemand
        for run in queryset:
            run_task_async_ondemand.send(str(run.uid))

    list_display = ['uid','job','status','export_formats','user','created_at','process_time','total_time']
    list_filter = ('status',)
    readonly_fields = ('uid','user','created_at')
    raw_id_fields = ('job',)
    search_fields = ['uid']
    actions = [start]
    ordering = ('-created_at',)

    def job_link(self, obj):
        return mark_safe('<a href="%s">Link to Job</a>' % \
                        reverse('admin:jobs_job_change',
                        args=(obj.job.id,)))

class ExportTaskAdmin(admin.ModelAdmin):
    list_display = ['uid','run','name','status','created_at','username','filesize_mb','duration']
    search_fields = ['uid','run__uid']
    list_filter = ('name','status')
    ordering = ('-created_at',)

class ExportRunsInline(admin.TabularInline):
    model = ExportRun
    readonly_fields = ('uid','user','status','created_at','change_link')
    extra = 0

    def change_link(self, obj):
        return mark_safe('<a href="%s">Link</a>' % \
                        reverse('admin:tasks_exportrun_change',
                        args=(obj.id,)))



class JobAdmin(GeoModelAdmin):
    """
    Admin model for editing Jobs in the admin interface.
    """
    def simplified_geom_raw(self, obj):
        return obj.simplified_geom.json

    search_fields = ['uid', 'name', 'user__username']
    list_display = ['uid', 'name', 'user']
    list_filter = ('pinned',)
    exclude = ['the_geom']
    raw_id_fields = ("user",)
    readonly_fields=('simplified_geom_raw',)
    inlines = [ExportRunsInline]

class HDXExportRegionAdmin(admin.ModelAdmin):
    raw_id_fields = ("job",)

class PartnerExportRegionAdmin(admin.ModelAdmin):
    raw_id_fields = ('job',)

class SavedFeatureSelectionAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    search_fields = ['name','description']
    list_filter = ('pinned',)
    list_display = [ 'name', 'description']

admin.site.register(Job, JobAdmin)
admin.site.register(HDXExportRegion, HDXExportRegionAdmin)
admin.site.register(PartnerExportRegion, PartnerExportRegionAdmin)
admin.site.register(ExportRun, ExportRunAdmin)
admin.site.register(ExportTask, ExportTaskAdmin)
admin.site.register(SavedFeatureSelection, SavedFeatureSelectionAdmin)
