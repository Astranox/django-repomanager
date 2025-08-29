from django.urls import path
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()

urlpatterns = [
    # Uncomment the next line to enable the admin:
    path('admin/', admin.site.urls),
]
urlpatterns += staticfiles_urlpatterns()
