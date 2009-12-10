from django.conf.urls.defaults import *
from SampleDB.samples.models import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    #(r'^SampleDB/', include('SampleDB.foo.urls')),
    #(r'^data/$', 'SampleDB.samples.views.slide_index'),
    #(r'^slides/$', 'SampleDB.samples.views.slide_index'),
    (r'^slides/$', 'django.views.generic.list_detail.object_list', {'queryset' : Slide.objects.all()}),
    (r'^slides/(?P<slideID>.*)$', 'SampleDB.samples.views.slide_detail'),
    #(r'^images/$', 'django.views.generic.list_detail.object_list', {'queryset' : Image.objects.all()}),
    #(r'^images/(?P<imageID>.*)$', 'SampleDB.samples.views.slide_detail'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     (r'^admin/(.*)', admin.site.root),

)