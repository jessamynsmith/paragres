paragres
========

Utility for synchronizing parallel PostgreSQL databases on Heroku and localhost

Features
--------

Easily copy databases between locations, e.g.:
* Initialize a Heroku database with local data
* Update local development database with the latest data in your Heroku app
* Update one Heroku app (e.g. staging) with the data from another app (e.g. production)


Installation
------------

You can get django-nose from PyPI with:

    pip install paragres

The development version can be installed with:

    pip install -e git://github.com/jessamynsmith/paragres.git#egg=paragres

If you are developing locally, your version can be installed from the working directory with:

    python setup.py.install


Use
---

Example 1, copying data between Heroku databases:

    paragres -s <source_heroku_app_name> -d <destination_heroku_app_name>

Example 2, copying data from a Heroku database to localhost:

    paragres -s <heroku_app_name> -t path/to/db_settings.py
    
db_settings.py must contain at least the following (Django settings file format):

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

|  |  | Destination |  |
| --- | --- | --- | --- |
|  |  | local database | Heroku app |
| --- | --- | --- | --- |
|  | local file | X |  |
|  | local database | X | X |
|  | url | X | X |
|  | Heroku app | X | X |
