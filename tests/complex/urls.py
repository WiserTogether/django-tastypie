from django.conf.urls import *

urlpatterns = patterns('',
    (r'^api/', include('complex.api.urls')),
)
