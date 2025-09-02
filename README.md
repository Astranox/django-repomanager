# django-repomanager (forked from mathiasertl/django-reprepro)

## Requirements

* Tested with Python 3.11
* [Django](https://www.djangoproject.com/) 5.0
* [python-debian](https://salsa.debian.org/python-debian-team/python-debian)
* [rpmfile](https://github.com/srossross/rpmfile)
* [reprepro](https://wiki.debian.org/DebianRepository/SetupWithReprepro) 5.2
* [createrepo_c](https://rpm-software-management.github.io/createrepo_c/) 1.2.1

## ChangeLog

### 0.2.1

** forked to django-repomanager
** updated Django, Python3, ..

### 0.2.0

** Support Python 3.5 and 3.7 (Python3 shipping with Debian Stretch and Buster)
** Drop support for Python 2.7
** Remove unused manage.py commands
** Update to Django 2.0/2.1
** Add `setup.py code_quality` command to test code with flake8 and isort
** Add tox configuration
