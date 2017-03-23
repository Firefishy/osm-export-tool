from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.contrib.gis.geos import GEOSGeometry

from .models import ExportConfig, ExportFormat, ExportProfile, Job

admin.site.register(ExportFormat)
admin.site.register(ExportProfile)


class JobAdmin(OSMGeoAdmin):
    """
    Admin model for editing Jobs in the admin interface.
    """
    search_fields = ['uid', 'name', 'user__username']
    list_display = ['uid', 'name', 'user']
    exclude = ['the_geom', 'the_geog']


class ExportConfigAdmin(admin.ModelAdmin):
    """
    Admin model for editing export configurations in the admin interface.
    """
    search_fields = ['uid', 'name', 'user__username']
    list_display = ['uid', 'name', 'user', 'config_type', 'published', 'created_at']

# register the new admin models
admin.site.register(Job, JobAdmin)
admin.site.register(ExportConfig, ExportConfigAdmin)
