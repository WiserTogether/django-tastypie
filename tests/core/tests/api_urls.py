from django.conf.urls import *
from core.tests.api import Api, NoteResource, UserResource


api = Api()
api.register(NoteResource())
api.register(UserResource())

urlpatterns = patterns('',
    (r'^api/', include(api.urls)),
)
