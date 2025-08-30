# This file is part of django-repomanager (https://github.com/Astranox/django-repomanager).
#
# django-repomanager is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# django-repomanager is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with django-repomanager.  If
# not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.utils.translation import gettext as _

from .constants import VENDOR_DEBIAN
from .constants import VENDOR_UBUNTU
from .constants import VENDOR_FEDORA
from .constants import VENDOR_REDHAT

VENDORS = (
    (VENDOR_DEBIAN, 'Debian'),
    (VENDOR_UBUNTU, 'Ubuntu'),
    (VENDOR_FEDORA, 'Fedora'),
    (VENDOR_REDHAT, 'RedHat'),
)


class Component(models.Model):
    name = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True)

    def __str__(self):
        return self.name


class Distribution(models.Model):
    name = models.CharField(max_length=64, unique=True)
    vendor = models.SmallIntegerField(choices=VENDORS)
    last_seen = models.DateTimeField(null=True)
    released = models.DateField(null=True, blank=True)
    supported_until = models.DateField(null=True, blank=True)

    components = models.ManyToManyField(Component, blank=True)

    def __str__(self):
        return self.name


class Package(models.Model):
    name = models.CharField(max_length=64, unique=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    all_components = models.BooleanField(
        default=False,
        help_text=_('If set, the package will be automatically added to all known components.')
    )
    all_distributions = models.BooleanField(
        default=False,
        help_text=_('If set, the package will be automatically added to all known distributions with same vendor.')
    )

    components = models.ManyToManyField(Component, blank=True)

    # Very useful if binary packages have individual changelogs where
    # the version is different from the source package version.
    remove_on_update = models.BooleanField(
        default=False,
        help_text="Remove package from index prior to adding a new version of the package."
    )

    def __str__(self):
        return self.name


class SourcePackage(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    dist = models.ForeignKey(Distribution, on_delete=models.CASCADE)
    components = models.ManyToManyField(Component)

    timestamp = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=32)

    def __str__(self):
        return '%s_%s' % (self.package.name, self.version)


class BinaryPackage(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)  # name of the binary package
    dist = models.ForeignKey(Distribution, on_delete=models.CASCADE)
    components = models.ManyToManyField(Component)

    timestamp = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=32)
    arch = models.CharField(max_length=8)

    def __str__(self):
        return '%s_%s_%s' % (self.name, self.version, self.arch)


class IncomingDirectory(models.Model):
    location = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.location
