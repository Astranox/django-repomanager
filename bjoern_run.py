#!/usr/bin/env python3

import bjoern

from packagearchive.wsgi import application

bjoern.run(application, "127.0.0.1", 8000)
