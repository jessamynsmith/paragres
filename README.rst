paragres
========

|Build Status| |Coverage Status| |PyPI Version| |Supported Versions|
|Downloads|

Utility for synchronizing parallel PostgreSQL databases on Heroku,
local, and remote servers

Features
--------

Easily copy databases between locations, e.g.:

- Initialize a Heroku database with local data
- Update local development database with the latest data in your Heroku app
- Update one Heroku app (e.g. staging) with the data from another app (e.g. production)

Installation
------------

You can get paragres from PyPI with:

::

    pip install paragres

The development version can be installed with:

::

    pip install -e git://github.com/jessamynsmith/paragres.git#egg=paragres

If you are developing locally, your version can be installed from the
working directory with:

::

    python setup.py.install

Use
---

Note 1: To use paragres to access a Heroku app, you must be logged into the Heroku account that
owns that app.

Note 2: By default, Heroku's new pg:backups command is used. if you want to use the old pgbackups
addon, you must specify --use-pgbackups

Example 1, copying data between Heroku databases:

::

    paragres -s <source_heroku_app_name> -d <destination_heroku_app_name>

Example 2, copying a new backup snapshot of data from a Heroku database
to localhost:

::

    paragres -s <heroku_app_name> -c -t path/to/db_settings.py

Example 3, creating a backup snapshot of a Heroku database:

::

    paragres -c -s <heroku_app_name>

db\_settings.py must contain at least the following (Django settings
file format):

::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': '<db_name>',
            'USER': '<username>',
            'PASSWORD': '<password>',
            'HOST': '<host>',
            'PORT': '<port>',
        }
    }

Supported transfers:

+--------------+--------------+---------------+--------------+
|              |              | Destination   |              |
+==============+==============+===============+==============+
|              |              | postgres      | Heroku app   |
+--------------+--------------+---------------+--------------+
| **Source**   | local file   | X             |              |
+--------------+--------------+---------------+--------------+
|              | postgres     | X             | X \*         |
+--------------+--------------+---------------+--------------+
|              | url          | X             | X            |
+--------------+--------------+---------------+--------------+
|              | Heroku app   | X             | X            |
+--------------+--------------+---------------+--------------+

\* Can only push from a database accessible to the local user, or
accessible to a user configured via PG\* environment variables

Development
-----------

Fork the project on github and git clone your fork, e.g.:

::

    git clone https://github.com/<username>/paragres.git

Create a virtualenv and install dependencies:

::

    mkvirtualenv paragres
    pip install -r requirements/package.txt -r requirements/test.txt

Run tests and view coverage:

::

    coverage run -m nose
    coverage report

Check code style:

::

    flake8

Install your local copy:

::

    python setup.py.install

.. |Build Status| image:: https://travis-ci.org/jessamynsmith/paragres.svg?branch=master
   :target: https://travis-ci.org/jessamynsmith/paragres
.. |Coverage Status| image:: https://coveralls.io/repos/jessamynsmith/paragres/badge.svg?branch=master
   :target: https://coveralls.io/r/jessamynsmith/paragres?branch=master
.. |PyPI Version| image:: https://pypip.in/version/paragres/badge.svg
   :target: https://pypi.python.org/pypi/paragres
.. |Supported Versions| image:: https://pypip.in/py_versions/paragres/badge.svg
   :target: https://pypi.python.org/pypi/paragres
.. |Downloads| image:: https://pypip.in/download/paragres/badge.svg
   :target: https://pypi.python.org/pypi/paragres
