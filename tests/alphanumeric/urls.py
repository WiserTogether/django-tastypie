from django.conf.urls import *

urlpatterns = patterns('',
    (r'^api/', include('alphanumeric.api.urls')),
)
