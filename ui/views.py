# -*- coding: utf-8 -*-
"""UI view definitions."""

from django.contrib.auth import logout as auth_logout
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from oauth2_provider.models import Application
from django.contrib import admin
from django.contrib.auth.admin import User, UserAdmin
from django.conf import settings

def authorized(request):
    # the user has now authorized a client application; they no longer need to
    # be logged into the site (and it will be confusing if they are, since
    # "logging out" of the UI just drops the auth token)
    auth_logout(request)
    return render(request, "ui/authorized.html")


def login(request):
    if not request.user.is_authenticated():
        # preserve redirects ("next" in request.GET)
        return redirect(
            reverse('osm:begin', args=['openstreetmap']) + '?' +
            request.GET.urlencode())
    else:
        return redirect('/v3/')


def logout(request):
    """Logs out user"""
    auth_logout(request)
    return redirect('/v3/')


def v3(request):
    ui_app = Application.objects.get(name='OSM Export Tool UI')

    context = dict(client_id=ui_app.client_id)
    if settings.MATOMO_URL is not None and settings.MATOMO_SITEID is not None:
        context.update({
            'MATOMO_URL': settings.MATOMO_URL,
            'MATOMO_SITEID': settings.MATOMO_SITEID
        })
    return render(request, 'ui/v3.html', context)


def redirect_to_v3(request):
    return redirect('/v3/')

class ApplicationAdmin(admin.ModelAdmin):
    raw_id_fields = ("user", )

admin.site.register(Application, ApplicationAdmin)
