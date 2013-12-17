from django.conf.urls import *

urlpatterns = patterns('',
    (r'^api/', include('gis.api.urls')),
)
