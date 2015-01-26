from mock import call, patch
import os
import tempfile
import unittest

from paragres.cli import create_parser
from paragres.command import Command


class StringStartsWith(str):
    def __eq__(self, other):
        return other.find(self) == 0


class TestDbSettings(unittest.TestCase):

    def setUp(self):
        parser = create_parser()
        self.command = Command(parser.parse_args([]))
        working_dir = os.path.realpath(os.path.dirname(__file__))
        self.data_dir = os.path.join(working_dir, 'data')
        self.settings = {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'dbname',
            'HOST': 'host',
            'USER': 'username',
            'PASSWORD': 'password',
            'PORT': 'port'
        }

    def test_parse_db_settings_django_settings_module(self):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'paragres.test.data.settings'

        settings = self.command.parse_db_settings('DJANGO_SETTINGS_MODULE')

        self.assertEqual(self.settings, settings)

    def test_parse_db_settings(self):
        settings = self.command.parse_db_settings(os.path.join(self.data_dir, 'settings.py'))

        self.assertEqual(self.settings, settings)

    @patch('paragres.command.Command.error')
    def test_parse_db_settings_invalid(self, mock_error):
        self.command.parse_db_settings(os.path.join(self.data_dir, 'invalid_settings.py'))

        mock_error.assert_called_once_with(StringStartsWith('Missing key or value for: default'))

    def test_initialize_db_args(self):
        self.command.initialize_db_args(self.settings, 'source')

        self.assertEqual('dbname', self.command.databases['source']['name'])
        expected_args = ['--user=username', '--host=host', '--port=port']
        self.assertEqual(expected_args, self.command.databases['source']['args'])
        self.assertEqual('password', self.command.databases['source']['password'])

    def test_initialize_db_args_db_name_already_set(self):
        self.command.databases['source']['name'] = 'bestdb'

        self.command.initialize_db_args(self.settings, 'source')

        self.assertEqual('bestdb', self.command.databases['source']['name'])

    def test_initialize_db_args_no_db_name_in_settings(self):
        self.settings['NAME'] = None

        self.command.initialize_db_args(self.settings, 'source')

        self.assertEqual(None, self.command.databases['source']['name'])

    def test_initialize_db_args_missing_key_in_settings(self):
        del self.settings['HOST']

        self.command.initialize_db_args(self.settings, 'source')

        expected_args = ['--user=username', '--port=port']
        self.assertEqual(expected_args, self.command.databases['source']['args'])

    def test_initialize_db_args_empty_value_in_settings(self):
        self.settings['HOST'] = None

        self.command.initialize_db_args(self.settings, 'source')

        expected_args = ['--user=username', '--port=port']
        self.assertEqual(expected_args, self.command.databases['source']['args'])


class TestFileCalls(unittest.TestCase):

    def setUp(self):
        parser = create_parser()
        self.command = Command(parser.parse_args([]))
        working_dir = os.path.realpath(os.path.dirname(__file__))
        self.data_dir = os.path.join(working_dir, 'data')

    @patch('time.strftime')
    def test_create_file_name(self, mock_strftime):
        mock_strftime.return_value = '2015-01-25-1734'

        filename = self.command.create_file_name('bestdb')

        self.assertEqual('bestdb-backup-2015-01-25-1734.sql', filename)
        mock_strftime.assert_called_once_with('%Y-%m-%d-%H%M')

    @patch('paragres.command.Command.error')
    @patch('urllib2.urlopen')
    def test_download_file_error(self, mock_urlopen, mock_error):
        mock_urlopen.side_effect = Exception('An error occurred!')

        self.command.download_file('http://example.com/', '')

        mock_urlopen.assert_called_once_with('http://example.com/')
        mock_error.assert_called_once_with('An error occurred!')

    @patch('urllib2.urlopen')
    def test_download_file_success(self, mock_urlopen):
        src_filename = os.path.join(self.data_dir, 'src.sql')
        mock_urlopen.return_value = open(src_filename)
        destination_file = tempfile.NamedTemporaryFile()

        self.command.download_file('http://example.com/', destination_file.name)

        mock_urlopen.assert_called_once_with('http://example.com/')
        self.assertEqual('PGDMP\n', destination_file.read())

    def test_unzip_file_if_necessary_not_zipped(self):
        compressed_filename = 'db.sql'

        result = self.command.unzip_file_if_necessary(compressed_filename)

        self.assertEqual(compressed_filename, result)

    @patch('subprocess.check_call')
    def test_unzip_file_if_necessary_zipped(self, mock_check_call):
        compressed_filename = 'db.sql.gz'

        result = self.command.unzip_file_if_necessary(compressed_filename)

        self.assertEqual('db.sql', result)
        mock_check_call.assert_called_once_with(['gunzip', '--force', compressed_filename])

    @patch('urllib2.urlopen')
    def test_download_file_from_url_no_source_app(self, mock_urlopen):
        src_filename = os.path.join(self.data_dir, 'src.sql')
        mock_urlopen.return_value = open(src_filename)

        result = self.command.download_file_from_url(None, 'http://www.example.com')

        # Don't want to leave SQL files around, cluttering things up
        os.remove(result)

        self.assertEqual('www_example_com-backup-', result[:23])
        mock_urlopen.assert_called_once_with('http://www.example.com')

    @patch('urllib2.urlopen')
    def test_download_file_from_url_with_source_app(self, mock_urlopen):
        src_filename = os.path.join(self.data_dir, 'src.sql')
        mock_urlopen.return_value = open(src_filename)

        result = self.command.download_file_from_url('app1', 'http://www.example.com')

        # Don't want to leave SQL files around, cluttering things up
        os.remove(result)

        self.assertEqual('app1-backup-', result[:12])
        mock_urlopen.assert_called_once_with('http://www.example.com')


class TestDbCalls(unittest.TestCase):

    def setUp(self):
        self.parser = create_parser()
        self.command = Command(self.parser.parse_args([]))

    @patch('subprocess.check_call')
    def test_dump_database_no_extra_args(self, mock_check_call):
        self.command.databases['source']['name'] = 'sourcedb'

        self.command.dump_database()

        expected_args = ['pg_dump', '-Fc', '--no-acl', '--no-owner', '--dbname=sourcedb',
                         StringStartsWith('--file=sourcedb-backup-')]
        mock_check_call.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_dump_database_with_extra_args(self, mock_check_call):
        self.command.databases['source']['name'] = 'sourcedb'
        self.command.databases['source']['args'] = ['--user=username']
        self.command.databases['source']['password'] = 'password'

        self.command.dump_database()

        self.assertEqual('password', os.environ.get('PGPASSWORD'))
        expected_args = ['pg_dump', '-Fc', '--no-acl', '--no-owner', '--dbname=sourcedb',
                         StringStartsWith('--file=sourcedb-backup-'), '--user=username']
        mock_check_call.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_drop_database_no_extra_args(self, mock_check_call):
        self.command.databases['destination']['name'] = 'destdb'

        self.command.drop_database()

        mock_check_call.assert_called_once_with(['dropdb', '--if-exists', 'destdb'])

    @patch('subprocess.check_call')
    def test_drop_database_with_extra_args(self, mock_check_call):
        self.command.databases['destination']['name'] = 'destdb'
        self.command.databases['destination']['args'] = ['--user=username']
        self.command.databases['destination']['password'] = 'password'

        self.command.drop_database()

        self.assertEqual('password', os.environ.get('PGPASSWORD'))
        expected_args = ['dropdb', '--if-exists', 'destdb', '--user=username']
        mock_check_call.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_create_database_no_extra_args(self, mock_check_call):
        self.command.databases['destination']['name'] = 'destdb'

        self.command.create_database()

        mock_check_call.assert_called_once_with(['createdb', 'destdb'])

    @patch('subprocess.check_call')
    def test_create_database_with_extra_args(self, mock_check_call):
        self.command.databases['destination']['name'] = 'destdb'
        self.command.databases['destination']['args'] = ['--user=username']
        self.command.databases['destination']['password'] = 'password'

        self.command.create_database()

        self.assertEqual('password', os.environ.get('PGPASSWORD'))
        expected_args = ['createdb', 'destdb', '--user=username', '--owner=username']
        mock_check_call.assert_called_once_with(expected_args)

    @patch('urllib2.urlopen')
    @patch('subprocess.check_call')
    def test_replace_postgres_db_url_file_source(self, mock_check_call, mock_urlopen):
        mock_urlopen.return_value = tempfile.NamedTemporaryFile()
        command = Command(self.parser.parse_args(['-u', 'http://www.example.com/', '-n', 'destdb']))

        command.replace_postgres_db('http://www.example.com/')

        expected_calls = [call(['dropdb', '--if-exists', 'destdb']),
                          call(['createdb', 'destdb']),
                          call(['pg_restore', '--no-acl', '--no-owner', '--dbname=destdb',
                                StringStartsWith('www_example_com-backup-')])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)

    @patch('urllib2.urlopen')
    @patch('subprocess.check_call')
    def test_replace_postgres_db_source(self, mock_check_call, mock_urlopen):
        mock_urlopen.return_value = tempfile.NamedTemporaryFile()
        command = Command(self.parser.parse_args(['-b', 'sourcedb', '-n', 'destdb']))

        command.replace_postgres_db(None)

        expected_calls = [call(['pg_dump', '-Fc', '--no-acl', '--no-owner', '--dbname=sourcedb',
                                StringStartsWith('--file=sourcedb-backup-')]),
                          call(['dropdb', '--if-exists', 'destdb']),
                          call(['createdb', 'destdb']),
                          call(['pg_restore', '--no-acl', '--no-owner', '--dbname=destdb',
                                StringStartsWith('sourcedb-backup-')])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)

    @patch('subprocess.check_call')
    def test_replace_postgres_local_file_source(self, mock_check_call):
        command = Command(self.parser.parse_args(['-f', 'db.sql', '-n', 'destdb']))

        command.replace_postgres_db(None)

        expected_calls = [call(['dropdb', '--if-exists', 'destdb']),
                          call(['createdb', 'destdb']),
                          call(['pg_restore', '--no-acl', '--no-owner', '--dbname=destdb',
                                'db.sql'])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)


class TestHerokuCalls(unittest.TestCase):

    def setUp(self):
        self.parser = create_parser()

    @patch('subprocess.check_output')
    def test_get_file_url_for_heroku_app(self, mock_check_output):
        mock_check_output.return_value = '  http://example.com/  '
        command = Command(self.parser.parse_args([]))

        url = command.get_file_url_for_heroku_app('app1')

        self.assertEqual('http://example.com/', url)
        expected_args = ['heroku', 'pgbackups:url', '--app=app1']
        mock_check_output.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_capture_heroku_database(self, mock_check_call):
        command = Command(self.parser.parse_args(['-s', 'app1']))

        command.capture_heroku_database()

        expected_args = ['heroku', 'pgbackups:capture', '--app=app1', '--expire']
        mock_check_call.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_reset_heroku_database(self, mock_check_call):
        command = Command(self.parser.parse_args(['-d', 'app2']))

        command.reset_heroku_database()

        expected_args = ['heroku', 'pg:reset', '--app=app2', 'DATABASE_URL']
        mock_check_call.assert_called_once_with(expected_args)

    @patch('subprocess.check_call')
    def test_replace_heroku_db_with_file_url(self, mock_check_call):
        command = Command(self.parser.parse_args(['-u', 'www.example.com', '-d', 'app2']))
        command.databases['source']['name'] = 'srcdb'

        command.replace_heroku_db('www.example.com')

        expected_calls = [call(['heroku', 'pg:reset', '--app=app2', 'DATABASE_URL']),
                          call(['heroku', 'pgbackups:restore', '--app=app2', 'DATABASE_URL',
                               '--confirm', 'app2', 'www.example.com'])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)

    @patch('subprocess.check_call')
    def test_replace_heroku_db_no_file_url(self, mock_check_call):
        command = Command(self.parser.parse_args(['-d', 'app2']))
        command.databases['source']['name'] = 'srcdb'

        command.replace_heroku_db(None)

        expected_calls = [call(['heroku', 'pg:reset', '--app=app2', 'DATABASE_URL']),
                          call(['heroku', 'pg:push', 'srcdb', 'DATABASE_URL', '--app=app2'])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)


class TestRun(unittest.TestCase):

    def setUp(self):
        self.parser = create_parser()

    @patch('subprocess.check_call')
    def test_run_nothing_to_do(self, mock_check_call):
        command = Command(self.parser.parse_args([]))

        command.run()

        self.assertEqual([], mock_check_call.call_args_list)

    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_run_destination_heroku(self, mock_check_call, mock_check_output):
        mock_check_output.return_value = '  http://example.com/  '
        command = Command(self.parser.parse_args(['-c', '-s', 'app1', '-d', 'app2']))
        command.databases['source']['name'] = 'srcdb'

        command.run()

        expected_calls = [call(['heroku', 'pgbackups:capture', '--app=app1', '--expire']),
                          call(['heroku', 'pg:reset', '--app=app2', 'DATABASE_URL']),
                          call(['heroku', 'pgbackups:restore', '--app=app2', 'DATABASE_URL',
                                '--confirm', 'app2', 'http://example.com/'])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)
        mock_check_output.assert_called_once_with(['heroku', 'pgbackups:url', '--app=app1'])

    @patch('subprocess.check_call')
    def test_run_destination_postgres(self, mock_check_call):
        working_dir = os.path.realpath(os.path.dirname(__file__))
        settings_file = os.path.join(working_dir, 'data', 'settings.py')
        command = Command(self.parser.parse_args(['-t', settings_file, '-o', settings_file,
                                                  '-b', 'sourcedb']))

        command.run()

        expected_calls = [
            call(['pg_dump', '-Fc', '--no-acl', '--no-owner', '--dbname=sourcedb',
                  StringStartsWith('--file=sourcedb-backup-'), '--user=username', '--host=host',
                  '--port=port']),
            call(['dropdb', '--if-exists', 'dbname', '--user=username', '--host=host',
                  '--port=port']),
            call(['createdb', 'dbname', '--user=username', '--host=host', '--port=port',
                  '--owner=username']),
            call(['pg_restore', '--no-acl', '--no-owner', '--dbname=dbname',
                  StringStartsWith('sourcedb-backup-'), '--user=username', '--host=host',
                  '--port=port'])]
        self.assertEqual(expected_calls, mock_check_call.call_args_list)
