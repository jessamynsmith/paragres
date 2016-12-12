import ast
import os
import sys
import subprocess
import time
try:
    # Python 3
    from urllib import parse as urlparse, request as urllib2
except ImportError:
    # Python 2
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
        self.databases = {
            'source': {
                'name': self.args.source_dbname,
                'args': [],
                'password': None,
            },
            'destination': {
                'name': self.args.dbname,
                'args': [],
                'password': None,
            }
        }

    def print_message(self, message, verbosity_needed=1):
        """ Prints the message, if verbosity is high enough. """
        if self.args.verbosity >= verbosity_needed:
            print(message)

    def error(self, message, code=1):
        """ Prints the error, and exits with the given code. """
        sys.stderr.write(message)
        sys.exit(code)

    def parse_db_settings(self, settings):
        """ Parse out database settings from filename or DJANGO_SETTINGS_MODULE. """
        if settings == 'DJANGO_SETTINGS_MODULE':
            django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
            self.print_message("Getting settings file from DJANGO_SETTINGS_MODULE=%s"
                               % django_settings)
            path_pieces = django_settings.split('.')
            path_pieces[-1] = '%s.py' % path_pieces[-1]
            settings = os.path.join(*path_pieces)

        self.print_message("Parsing settings from settings file '%s'" % settings)
        parser = DatabaseSettingsParser()
        with open(settings) as settings_file:
            settings_ast = ast.parse(settings_file.read())
            parser.visit(settings_ast)

        try:
            return parser.database_settings['default']
        except KeyError as e:
            self.error("Missing key or value for: %s\nSettings must be of the form: %s"
                       % (e, self.settings_format))

    def initialize_db_args(self, settings, db_key):
        """ Initialize connection arguments for postgres commands. """
        self.print_message("Initializing database settings for %s" % db_key, verbosity_needed=2)

        db_member = self.databases[db_key]

        db_name = settings.get('NAME')
        if db_name and not db_member['name']:
            db_member['name'] = db_name

        db_member['password'] = settings.get('PASSWORD')

        args = []
        for key in ['USER', 'HOST', 'PORT']:
            value = settings.get(key)
            if value:
                self.print_message("Adding parameter %s" % key.lower, verbosity_needed=2)
                args.append('--%s=%s' % (key.lower(), value))

        db_member['args'] = args

    def export_pgpassword(self, db_key):
        if self.databases[db_key]['password']:
            self.print_message("Exporting PGPASSWORD", verbosity_needed=2)
            os.environ['PGPASSWORD'] = self.databases[db_key]['password']

    def create_file_name(self, backup_name):
        """ Create timestamped backup file name. """
        timestamp = time.strftime('%Y-%m-%d-%H%M')
        return '%s-backup-%s.sql' % (backup_name, timestamp)

    def download_file(self, url, filename):
        """ Download file from url to filename. """
        self.print_message("Downloading to file '%s' from URL '%s'" % (filename, url))
        try:
            db_file = urllib2.urlopen(url)
            with open(filename, 'wb') as output:
                output.write(db_file.read())
            db_file.close()
        except Exception as e:
            self.error(str(e))
        self.print_message("File downloaded")

    def unzip_file_if_necessary(self, source_file):
        """ Unzip file if zipped. """
        if source_file.endswith(".gz"):
            self.print_message("Decompressing '%s'" % source_file)
            subprocess.check_call(["gunzip", "--force", source_file])
            source_file = source_file[:-len(".gz")]
        return source_file

    def download_file_from_url(self, source_app, url):
        """ Download file from source app or url, and return local filename. """
        if source_app:
            source_name = source_app
        else:
            source_name = urlparse.urlparse(url).netloc.replace('.', '_')

        filename = self.create_file_name(source_name)
        self.download_file(url, filename)
        return filename

    def dump_database(self):
        """ Create dumpfile from postgres database, and return filename. """
        db_file = self.create_file_name(self.databases['source']['name'])
        self.print_message("Dumping postgres database '%s' to file '%s'"
                           % (self.databases['source']['name'], db_file))
        self.export_pgpassword('source')
        args = [
            "pg_dump",
            "-Fc",
            "--no-acl",
            "--no-owner",
            "--dbname=%s" % self.databases['source']['name'],
            "--file=%s" % db_file,
        ]
        args.extend(self.databases['source']['args'])
        subprocess.check_call(args)
        return db_file

    def drop_database(self):
        """ Drop postgres database. """
        self.print_message("Dropping database '%s'" % self.databases['destination']['name'])
        self.export_pgpassword('destination')
        args = [
            "dropdb",
            "--if-exists",
            self.databases['destination']['name'],
        ]
        args.extend(self.databases['destination']['args'])
        subprocess.check_call(args)

    def create_database(self):
        """ Create postgres database. """
        self.print_message("Creating database '%s'" % self.databases['destination']['name'])
        self.export_pgpassword('destination')
        args = [
            "createdb",
            self.databases['destination']['name'],
        ]
        args.extend(self.databases['destination']['args'])
        for arg in self.databases['destination']['args']:
            if arg[:7] == '--user=':
                args.append('--owner=%s' % arg[7:])
        subprocess.check_call(args)

    def replace_postgres_db(self, file_url):
        """ Replace postgres database with database from specified source. """
        self.print_message("Replacing postgres database")

        if file_url:
            self.print_message("Sourcing data from online backup file '%s'" % file_url)
            source_file = self.download_file_from_url(self.args.source_app, file_url)
        elif self.databases['source']['name']:
            self.print_message("Sourcing data from database '%s'"
                               % self.databases['source']['name'])
            source_file = self.dump_database()
        else:
            self.print_message("Sourcing data from local backup file %s" % self.args.file)
            source_file = self.args.file

        self.drop_database()
        self.create_database()

        source_file = self.unzip_file_if_necessary(source_file)

        self.print_message("Importing '%s' into database '%s'"
                           % (source_file, self.databases['destination']['name']))
        args = [
            "pg_restore",
            "--no-acl",
            "--no-owner",
            "--dbname=%s" % self.databases['destination']['name'],
            source_file,
        ]
        args.extend(self.databases['destination']['args'])
        subprocess.check_call(args)

    def get_file_url_for_heroku_app(self, source_app):
        """ Get latest backup URL from heroku pg:backups (or pgbackups). """
        self.print_message("Getting backup url for Heroku app '%s'" % source_app)
        args = [
            "heroku",
            "pg:backups:url",
            "--app=%s" % source_app,
        ]
        if self.args.use_pgbackups:
            args = [
                "heroku",
                "pgbackups:url",
                "--app=%s" % source_app,
            ]
        return subprocess.check_output(args).strip().decode('ascii')

    def capture_heroku_database(self):
        """ Capture Heroku database backup. """
        self.print_message("Capturing database backup for app '%s'" % self.args.source_app)
        args = [
            "heroku",
            "pg:backups:capture",
            "--app=%s" % self.args.source_app,
        ]
        if self.args.use_pgbackups:
            args = [
                "heroku",
                "pgbackups:capture",
                "--app=%s" % self.args.source_app,
                "--expire",
            ]
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

    def replace_heroku_db(self, file_url):
        """ Replace Heroku database with database from specified source. """
        self.print_message("Replacing database for Heroku app '%s'" % self.args.destination_app)

        self.reset_heroku_database()

        if file_url:
            self.print_message("Restoring from URL '%s'" % file_url)
            args = [
                "heroku",
                "pg:backups:restore",
                file_url,
                "--app=%s" % self.args.destination_app,
                "DATABASE",
                "--confirm",
                self.args.destination_app,
            ]
            if self.args.use_pgbackups:
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
            # TODO perhaps add support for file -> heroku by piping to pg:psql
            self.print_message("Pushing data from database '%s'" % self.databases['source']['name'])
            self.print_message("NOTE: Any postgres authentication settings you passed to paragres "
                               "will be ignored.\nIf desired, you can export PG* variables.\n"
                               "You will be prompted for your psql password.")
            args = [
                "heroku",
                "pg:push",
                self.databases['source']['name'],
                "DATABASE_URL",
                "--app=%s" % self.args.destination_app,
            ]
            subprocess.check_call(args)

    def run(self):
        """ Replace a database with the data from the specified source. """
        self.print_message("\nBeginning database replacement process.\n")

        if self.args.source_settings:
            settings = self.parse_db_settings(self.args.source_settings)
            self.initialize_db_args(settings, 'source')

        if self.args.settings:
            settings = self.parse_db_settings(self.args.settings)
            self.initialize_db_args(settings, 'destination')

        if self.args.capture:
            self.capture_heroku_database()

        file_url = self.args.url
        if self.args.source_app:
            self.print_message("Sourcing data from backup for Heroku app '%s'"
                               % self.args.source_app)
            file_url = self.get_file_url_for_heroku_app(self.args.source_app)

        if self.args.destination_app:
            self.replace_heroku_db(file_url)
        elif self.databases['destination']['name']:
            self.replace_postgres_db(file_url)

        self.print_message("\nDone.\n\nDon't forget to update the Django Site entry if necessary!")
