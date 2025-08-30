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

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RepomanagerConfig(AppConfig):
    name = 'repomanager'
    verbose_name = _('Package repositories')
