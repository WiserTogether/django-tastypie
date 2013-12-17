from django.conf.urls import *
from core.tests.resources import NoteResource


note_resource = NoteResource()

urlpatterns = patterns('',
    (r'^', include(note_resource.urls)),
)
