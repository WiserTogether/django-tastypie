from django.conf.urls import *

urlpatterns = patterns('',
    (r'^api/', include('basic.api.urls')),
)
