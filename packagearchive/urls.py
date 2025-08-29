from django.urls import path
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    # Uncomment the next line to enable the admin:
    path('admin/', admin.site.urls),
]
