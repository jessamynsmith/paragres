import ast
import os
import sys
import subprocess
import time
import urllib2
import urlparse


class DatabaseSettingsParser(ast.NodeVisitor):
    database_settings = None

    def visit_Assign(self, node):
        for target in node.targets:
            if target.id == "DATABASES":
                self.database_settings = ast.literal_eval(node.value)


class Command(object):
    settings_format = """
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': '<db_name>',
            'USER': '<username>',
            'PASSWORD': '<password>',
            'HOST': '<host>',
            'PORT': '<port>',
        }
    }"""

    def __init__(self, args):
        self.args = args
        self.db_settings = {}
        self.db_name = self.args.dbname

    def print_message(self, message):
        """ Prints the message, if verbosity is high enough. """
        if self.args.verbosity > 0:
            print message

    def error(self, message, code=1):
        """ Prints the error, and exits with the given code. """
        print >>sys.stderr, message
        sys.exit(code)

    def initialize_db_settings(self):
        """ Parse out database settings from filename or DJANGO_SETTINGS_MODULE. """
        settings = self.args.settings
        if settings == 'DJANGO_SETTINGS_MODULE':
            django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
            self.print_message("Getting settings file from DJANGO_SETTINGS_MODULE=%s"
                               % django_settings)
            path_pieces = django_settings.split('.')
            path_pieces[-1] = '%s.py' % path_pieces[-1]
            settings = os.path.join(*path_pieces)

        self.print_message("Parsing settings from settings file '%s'" % settings)
        settings_file = open(settings)
        settings_ast = ast.parse(settings_file.read())
        parser = DatabaseSettingsParser()
        parser.visit(settings_ast)

        try:
            self.db_settings = parser.database_settings['default']
            self.db_name = self.db_settings['NAME']
        except KeyError as e:
            self.error('Missing key or value for: %s\nSettings must be of the form: %s'
                       % (e.message, self.settings_format))

    def set_postgres_env_vars(self):
        """ Set environment variables for postgres commands. """
        self.print_message("Setting PostgreSQL environment variables")
        for key in ['USER', 'PASSWORD', 'HOST', 'PORT']:
            value = self.db_settings.get(key)
            if value:
                env_var = 'PG%s' % key
                self.print_message("Setting %s" % env_var)
                os.environ[env_var] = value

    def get_file_url_for_app(self, source_app):
        """ Get latest backup URL from heroku pgbackups. """
        self.print_message("Using pgbackups to get backup url for Heroku app '%s'" % source_app)
        args = [
            "heroku",
            "pgbackups:url",
            "--app=%s" % source_app,
        ]
        return subprocess.check_output(args).strip()

    def create_file_name(self, backup_name):
        """ Create timestamped backup file name. """
        timestamp = time.strftime('%Y-%m-%d-%H%M')
        return '%s-backup-%s.sql' % (backup_name, timestamp)

    def download_file(self, url, filename):
        """ Download file from url to filename. """
        self.print_message("Downloading to file '%s' from URL '%s'" % (filename, url))
        try:
            db_file = urllib2.urlopen(url)
            output = open(filename, 'wb')
            output.write(db_file.read())
            output.close()
        except Exception as e:
            self.error(str(e))
        self.print_message("File downloaded")

    def unzip_file_if_necessary(self, source_file):
        """ Unzip file if zipped. """
        if source_file.endswith(".gz"):
            self.print_message("Decompressing %s" % source_file)
            subprocess.check_call(["gunzip", "--force", source_file])
            source_file = source_file[:-len(".gz")]
        return source_file

    def download_from_url(self, source_app, url):
        """ Download file from source app or url, and return local filename. """
        if source_app:
            source_name = source_app
        else:
            source_name = urlparse.urlparse(url).netloc

        filename = self.create_file_name(source_name)
        self.download_file(url, filename)
        return filename

    def dump_database(self, db_name):
        """ Create dumpfile from local database, and return filename. """
        db_file = self.create_file_name('localhost')
        self.print_message("Dumping local database '%s' to file '%s'" % (db_name, db_file))
        args = [
            "pg_dump",
            "-Fc",
            "--no-acl",
            "--no-owner",
            "--dbname=%s" % db_name,
            "--file=%s" % db_file,
        ]
        subprocess.check_call(args)
        return db_file

    def drop_database(self):
        """ Drop local database. """
        self.print_message("Dropping database '%s'" % self.db_name)
        try:
            args = [
                "dropdb",
                self.db_name,
            ]
            subprocess.check_call(args)
        except subprocess.CalledProcessError:
            # Probably failed because the db did not exist to be dropped.
            pass

    def create_database(self):
        """ Create local database. """
        self.print_message("Creating database '%s'" % self.db_name)
        args = [
            "createdb",
            self.db_name,
        ]
        user = self.db_settings.get('USER')
        if user:
            args.append("--owner=%s" % user)
        subprocess.check_call(args)

    def reset_heroku_database(self):
        """ Reset Heroku database. """
        self.print_message("Resetting database for app '%s'" % self.args.destination_app)
        args = [
            "heroku",
            "pg:reset",
            "--app=%s" % self.args.destination_app,
            "DATABASE_URL",
        ]
        subprocess.check_call(args)

    def replace_heroku_db(self):
        """ Replace Heroku database with database from specified source. """
        self.print_message("Replacing database for Heroku app '%s'" % self.args.destination_app)

        file_url = self.args.url
        if self.args.source_app:
            file_url = self.get_file_url_for_app(self.args.source_app)

        self.reset_heroku_database()

        if file_url:
            self.print_message("Restoring from URL '%s'" % file_url)
            args = [
                "heroku",
                "pgbackups:restore",
                "--app=%s" % self.args.destination_app,
                "DATABASE_URL",
                "--confirm",
                self.args.destination_app,
                file_url,
            ]
            subprocess.check_call(args)
        else:
            self.print_message("Pushing data from local database '%s'" % self.args.local_db)
            args = [
                "heroku",
                "pg:push",
                self.args.local_db,
                "DATABASE_URL",
                "--app=%s" % self.args.destination_app,
            ]
            subprocess.check_call(args)

    def replace_local_db(self):
        """ Replace local database with database from specified source. """
        self.print_message("Replacing localhost database")

        file_url = self.args.url
        if self.args.source_app:
            self.print_message("Sourcing data from backup for Heroku app '%s'"
                               % self.args.source_app)
            file_url = self.get_file_url_for_app(self.args.source_app)

        if file_url:
            self.print_message("Sourcing data from online backup file '%s'" % file_url)
            source_file = self.download_from_url(self.args.source_app, file_url)
        elif self.args.local_db:
            self.print_message("Sourcing data from local database '%s'" % self.args.local_db)
            source_file = self.dump_database(self.db_name)
        else:
            source_file = self.args.file
            self.print_message("Sourcing data from local backup file %s" % source_file)

        self.drop_database()
        self.create_database()

        source_file = self.unzip_file_if_necessary(source_file)

        self.print_message("Importing '%s' into database '%s'" % (source_file, self.db_name))
        args = [
            "pg_restore",
            "--no-acl",
            "--no-owner",
            "--dbname=%s" % self.db_name,
            source_file,
        ]
        subprocess.check_call(args)

    def run(self):
        """ Replace a database with the data from the specified source. """
        self.print_message("\nBeginning database replacement process.\n")

        if self.args.settings:
            self.initialize_db_settings()
            self.set_postgres_env_vars()

        if self.args.destination_app:
            self.replace_heroku_db()
        else:
            self.replace_local_db()

        self.print_message("\nDone.\n\nDon't forget to update the Django Site entry if necessary!")
