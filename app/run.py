#!/usr/bin/env python
from os import environ

from views import app, mysql
app.run(host='0.0.0.0', port=8000)
