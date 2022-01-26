# This file is part of django-reprepro (https://github.com/mathiasertl/django-reprepro).
#
# django-reprepro is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# django-reprepro is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with django-reprepro.  If
# not, see <http://www.gnu.org/licenses/>.

import glob
import os
import re
import time
from subprocess import PIPE
from subprocess import Popen

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import BinaryPackage
from ...models import Distribution
from ...models import IncomingDirectory
from ...models import Package
from ...models import SourcePackage
from ...util import ChangesFile
from ...constants import VENDOR_DEBIAN, VENDOR_UBUNTU, VENDOR_FEDORA, VENDOR_REDHAT

# NOTE 2016-01-15: We add --ignore=surprisingbinary because of automatically generated
#   -dbgsym packages, which are not included in the changes file. See
#   https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=808558 for more info. This is fixed
#   in reprepro 4.17.0.
# NOTE 2018-01-14: Add --ignore=wrongdistribution because packages now always name "unstable"
#   in the changelog.
BASE_ARGS = ['reprepro', '-b', settings.APT_BASEDIR, '--ignore=surprisingbinary',
             '--ignore=wrongdistribution']

class Command(BaseCommand):
    help = 'Process incoming files'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help="Don't really add any files.")
        parser.add_argument(
            '--prerm', default='',
            help="Comma-seperated list of source packages to remove before "
                 "adding them. Necessary for source packages that build"
                 "several binary packages with new versions."
        )
        parser.add_argument('--norm', default=False, action='store_true',
                            help="Don't remove files after adding them to the repository.")

    def err(self, msg):
        self.stderr.write("%s\n" % msg)

    def rm(self, path):
        """Remove a file. Honours --dry, --norm and --verbose."""
        if self.norm:
            return
        if not self.dry:
            os.remove(path)

    def ex(self, *args):
        if self.verbose:
            print(' '.join(args))
        if not self.dry:
            p = Popen(args, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            return p.returncode, stdout, stderr
        else:
            return 0, '', ''

    def remove_src_package(self, pkg, dist):
        """Remove a source package from a distribution."""

        cmd = BASE_ARGS + ['removesrc', dist.name, pkg]
        return self.ex(*cmd)

    def include(self, dist, component, changesfile):
        """Add a .changes file to the repository."""

        cmd = BASE_ARGS + ['-C', component.name, 'include', dist.name, changesfile.path]
        return self.ex(*cmd)

    def includedeb(self, dist, component, changes, deb):
        path = os.path.join(os.path.dirname(changes.path), deb)
        cmd = BASE_ARGS + ['-C', component.name, 'includedeb', dist.name, path]
        return self.ex(*cmd)

    def record_source_upload(self, package, changes, dist, components):
        version = changes['Version'].rsplit('-', 1)[0]
        p, created = SourcePackage.objects.get_or_create(package=package, dist=dist, defaults={
            'version': version,
        })
        if not created:
            p.version = version
            p.components.clear()
            p.timestamp = timezone.now()
            p.save()

        p.components.add(*components)
        return p

    def record_binary_upload(self, deb, package, dist, components):
        # parse name, version and arch from the filename
        match = re.match('(?P<name>.*)_(?P<version>.*)_(?P<arch>.*).deb', deb)
        name = match.group('name')
        version = match.group('version')
        arch = match.group('arch')

        p, created = BinaryPackage.objects.get_or_create(
            package=package, name=name, dist=dist, arch=arch, defaults={
                'version': version,
            })
        if not created:
            p.version = version
            p.components.clear()
            p.timestamp = timezone.now()
            p.save()

        p.components.add(*components)
        return p

    def handle_changesfile(self, changesfile, dist, arch):
        pkg = ChangesFile(changesfile)
        pkg.parse()

        srcpkg = pkg['Source']
        package = Package.objects.get_or_create(name=srcpkg)[0]
        package.last_seen = timezone.now()
        package.save()

        # get list of components
        if package.all_components:
            components = dist.components.filter(enabled=True)
        else:
            components = package.components.order_by('name').filter(distribution=dist)
            components.update(last_seen=timezone.now())
        if self.verbose:
            print('%s: %s' % (dist, ', '.join([c.name for c in components])))

        # see if all files exist. If not, try a few more times, we might be in
        # the middle of uploading a new package.
        for i in range(1, 5):
            if pkg.exists():
                break
            else:
                if self.verbose:
                    self.err('%s: Not all files exist, try again in 5s...'
                             % changesfile)
                time.sleep(5)

        # remove package if requested
        if srcpkg in self.prerm or package.remove_on_update:
            self.remove_src_package(pkg=srcpkg, dist=dist)

        totalcode = 0

        for component in components:
            if arch == 'amd64':
                code, stdout, stderr = self.include(dist, component, pkg)
                totalcode += code

                if code == 0:
                    self.record_source_upload(package, pkg, dist, components)
                    for deb in pkg.binary_packages:
                        self.record_binary_upload(deb, package, dist, components)
                else:
                    self.err('   ... RETURN CODE: %s' % code)
                    self.err('   ... STDOUT: %s' % stdout.decode('utf-8'))
                    self.err('   ... STDERR: %s' % stderr.decode('utf-8'))
            else:
                debs = [f for f in pkg.binary_packages if f.endswith('_%s.deb' % arch)]
                for deb in debs:
                    code, stdout, stderr = self.includedeb(dist, component, pkg, deb)
                    totalcode += code

                    if code == 0:
                        self.record_binary_upload(deb, package, dist, components)
                    else:
                        self.err('   ... RETURN CODE: %s' % code)
                        self.err('   ... STDOUT: %s' % stdout.decode('utf-8'))
                        self.err('   ... STDERR: %s' % stderr.decode('utf-8'))

        if totalcode == 0:
            # remove changes files and the files referenced:
            basedir = os.path.dirname(changesfile)
            for filename in pkg.files:
                self.rm(os.path.join(basedir, filename))

            self.rm(changesfile)

    def handle_rpm_file(self, rpmfile, package, dist, pkgmatch):
        name = pkgmatch.group('name')
        version = pkgmatch.group('version')
        release = pkgmatch.group('release')
        arch = pkgmatch.group('arch')

        # check signature
        command = ["rpm", "--quiet", "--checksig", rpmfile]
        code, stdout, stderr = self.ex(*command)

        if code != 0:
            self.err('Signature for {} is invalid'.format(rpmfile))
            return None

        # copy to proper location
        target = f"{name}-{version}-{release}.{dist.name}.{arch}.rpm"
        command = ["cp", "-a", rpmfile, f"{settings.RPM_BASEDIR}/rpms/{target}"]
        code, stdout, stderr = self.ex(*command)
        if code != 0:
            self.err(f"Couldn't copy file {rpmfile} to {settings.RPM_BASEDIR}/rpms/.")
            self.err(f"command: {command}")
            self.err(f"target: {target}")
            return None

        # remove rpm file:
        self.rm(rpmfile)

        return target

    def handle_rpm_distribution(self, rpmfile, package, dist, pkgmatch, target):
        dir = pkgmatch.group('dir')
        name = pkgmatch.group('name')
        version = pkgmatch.group('version')
        release = pkgmatch.group('release')
        arch = pkgmatch.group('arch')

        # get list of components
        if arch == "noarch":
            components = dist.components.filter(enabled=True)
        else:
            components = dist.components.filter(enabled=True, name__endswith=f"-{arch}")
        if not package.all_components:
            specific_components = package.components.order_by('name').filter(distribution=dist, name__endswith=f"-{arch}")
            if len(specific_components) > 0:
                specific_components.update(last_seen=timezone.now())
                components = specific_components
        if self.verbose:
            print('%s: %s' % (dist, ', '.join([c.name for c in components])))

        if arch == "src":
            p, created = SourcePackage.objects.get_or_create(package=package, dist=dist, version=f"{version}-{release}")
        else:
            p, created = BinaryPackage.objects.get_or_create(package=package, name=name, dist=dist, arch=arch, version=f"{version}-{release}")
        if not created:
            p.components.clear()
            p.timestamp = timezone.now()
            p.save()

        p.components.add(*components)

        for component in components:
            if self.verbose:
                print(target)
            linkpath = f"{settings.RPM_BASEDIR}/{component.name}/{name}-{version}-{release}.{dist.name}.{arch}.rpm"
            if self.verbose:
                print(linkpath)
            os.symlink(f"{settings.RPM_BASEDIR}/rpms/{target}", linkpath)


    def handle_directory(self, path):
        dist, arch = os.path.basename(path).split('-', 1)
        dist = Distribution.objects.get(name=dist)

        for f in [f for f in os.listdir(path) if f.endswith('.changes')]:
            dist.last_seen = timezone.now()
            try:
                self.handle_changesfile(os.path.join(path, f), dist, arch)
            except RuntimeError as e:
                self.err(e)

        dist.save()

    def handle_incoming(self, incoming):
        # A few safety checks:
        if not os.path.exists(incoming.location):
            self.err("%s: No such directory." % incoming.location)
            return
        if not os.path.isdir(incoming.location):
            self.err("%s: Not a directory." % incoming.location)
            return

        location = os.path.abspath(incoming.location)

        deb_paths = []
        rpm_paths = []
        for dirname in sorted(os.listdir(location)):
            path = os.path.join(location, dirname)
            if os.path.isdir(path) and '-' in path:
                deb_paths.append(path)
            elif os.path.isfile(path) and path.endswith(".rpm"):
                rpm_paths.append(path)

        # handle debian stuff
        for path in deb_paths:
            self.handle_directory(path)

        # handle rpm stuff
        if len(rpm_paths) > 0:
            # ensure paths
            dists = Distribution.objects.filter(vendor__in=[VENDOR_FEDORA,VENDOR_REDHAT])
            for dist in dists:
                for component in dist.components.all():
                    command = ["mkdir", "-p", f"{settings.RPM_BASEDIR}/{component.name}"]
                    self.ex(*command)
            command = ["mkdir", "-p", f"{settings.RPM_BASEDIR}/rpms/"]
            self.ex(*command)

        for path in rpm_paths:
            try:
                # parse name, version and arch from the filename
                pkgmatch = re.match('^(?P<dir>.*)/(?P<name>[^/]*)-(?P<version>[^-/]*)-(?P<release>[^-/]*)\.(?P<dist>[^./]*)\.(?P<arch>[^/]*)\.rpm$', path)
                dir = pkgmatch.group('dir')
                name = pkgmatch.group('name')
                version = pkgmatch.group('version')
                release = pkgmatch.group('release')
                dist = pkgmatch.group('dist')
                arch = pkgmatch.group('arch')

                dist = Distribution.objects.get(name=dist)

                # find package name from file name
                package = None
                if arch == "src":
                    pkgs = SourcePackage.objects.filter(package__name=name)
                    pkgs_dist = pkgs.filter(dist=dist)
                    if len(pkgs_dist) > 0:
                        package = pkgs_dist[0].package
                    elif len(pkgs) > 0:
                        package = pkgs[0].package
                else:
                    pkgs = BinaryPackage.objects.filter(name=name)
                    pkgs_dist = pkgs.filter(dist=dist)
                    pkgs_arch = pkgs_dist.filter(arch=arch)
                    if len(pkgs_arch) > 0:
                        package = pkgs_arch[0].package
                    elif len(pkgs_dist) > 0:
                        package = pkgs_dist[0].package
                    elif len(pkgs) > 0:
                        package = pkgs[0].package

                if package is None:
                    package = Package.objects.get_or_create(name=name)[0]

                package.last_seen = timezone.now()
                package.save()

                # remove package if requested
                if package.name in self.prerm or package.remove_on_update:
                    storagefiles = glob.glob(f"{settings.RPM_BASEDIR}/rpms/{name}-*-*.*.*.rpm")
                    for file in storagefiles:
                        self.rm(file)
                    for srcpkg in SourcePackage.objects.filter(package__name=package.name, dist__vendor__in=[VENDOR_FEDORA, VENDOR_REDHAT]):
                        for component in srcpkg.components.all():
                            fn = f"{settings.RPM_BASEDIR}/{component.name}/{srcpkg.name}-{srcpkg.version}.{srcpkg.dist.name}.src.rpm"
                            if os.path.exists(fn):
                                self.rm(fn)
                        if not self.dry:
                            srcpkg.delete()
                    for binpkg in BinaryPackage.objects.filter(package__name=package.name, dist__vendor__in=[VENDOR_FEDORA, VENDOR_REDHAT]):
                        for component in binpkg.components.all():
                            fn = f"{settings.RPM_BASEDIR}/{component.name}/{binpkg.name}-{binpkg.version}.{binpkg.dist.name}.{binpkg.arch}.rpm"
                            if os.path.exists(fn):
                                self.rm(fn)
                        if not self.dry:
                            binpkg.delete()

                target = self.handle_rpm_file(path, package, dist, pkgmatch)
                if target is None:
                    self.err("Couldn't create link target rpm file.")
                    continue

                dists = [dist]
                if package.all_distributions:
                    dists = Distribution.objects.filter(vendor=dist.vendor)

                for d in dists:
                    d.last_seen = timezone.now()
                    d.save()
                    self.handle_rpm_distribution(path, package, d, pkgmatch, target)

            except RuntimeError as e:
                self.err(e)

        if len(rpm_paths) > 0:
            # regenerate / update all components
            dists = Distribution.objects.filter(vendor__in=[VENDOR_FEDORA,VENDOR_REDHAT])
            for dist in dists:
                for component in dist.components.all():
                    command = ["createrepo", "-d", "--basedir", f"{settings.RPM_BASEDIR}/{component.name}", "--update", "."]
                    self.ex(*command)

    def handle(self, *args, **options):
        self.verbose = options['verbosity'] >= 2
        self.dry = options['dry_run']
        self.norm = options['norm']
        self.prerm = options['prerm'].split(',')
        self.src_handled = {}

        directories = IncomingDirectory.objects.filter(enabled=True)

        for directory in directories.order_by('location'):
            self.handle_incoming(directory)
