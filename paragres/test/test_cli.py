from mock import call, patch
import sys
import unittest

from paragres import cli


# Extract these to package, maybe even submit pr to mock
class StringStartsWith(str):
    def __eq__(self, other):
        return other.find(self) == 0


class TestCli(unittest.TestCase):

    def setUp(self):
        self.parser = cli.create_parser()

    def test_verify_args_no_destination(self):
        args = self.parser.parse_args([])

        error_message = cli.verify_args(args)

        expected_error = ('A postgres destination requires either a database name (-n) or a '
                          'settings file containing one (-t)')
        self.assertEqual(expected_error, error_message)

    def test_verify_args_capture_only(self):
        args = self.parser.parse_args(['-c'])

        error_message = cli.verify_args(args)

        expected_error = 'Heroku backup capture requires a source Heroku app (-s)'
        self.assertEqual(expected_error, error_message)

    def test_verify_args_capture_from_source(self):
        args = self.parser.parse_args(['-c', '-s', 'app1'])

        error_message = cli.verify_args(args)

        self.assertEqual(None, error_message)

    def test_verify_args_correct_single_source(self):
        args = self.parser.parse_args(['-n', 'destdb', '-s', 'app1'])

        error_message = cli.verify_args(args)

        self.assertEqual(None, error_message)

    def test_verify_args_too_many_sources(self):
        args = self.parser.parse_args(['-n', 'destdb', '-s', 'app1', '-b', 'sourcedb'])

        error_message = cli.verify_args(args)

        expected_error = ('A postgres destination requires a single source, one of file (-f), '
                          'url (-u), Heroku app (-s), db name (-b) or db settings (-o)')
        self.assertEqual(expected_error, error_message)

    def test_verify_args_heroku_destination_correct_single_source(self):
        args = self.parser.parse_args(['-n destdb', '-b sourcedb', '-d app2'])

        error_message = cli.verify_args(args)

        self.assertEqual(None, error_message)

    def test_verify_args_heroku_destination_too_many_source(self):
        args = self.parser.parse_args(['-n', 'destdb', '-s', 'app1', '-b', 'srcedb', '-d', 'app2'])

        error_message = cli.verify_args(args)

        expected_error = ('A Heroku app destination requires a single source, one of url (-u), '
                          'Heroku app (-s), db name (-b) or db settings (-o)')
        self.assertEqual(expected_error, error_message)

    @patch('argparse.ArgumentParser.exit')
    def test_error(self, mock_exit):
        cli.error(self.parser, 'An error occurred!')

        mock_exit.assert_called_once_with(message='\nERROR: An error occurred!\n')

    def test_main(self):
        try:
            cli.main()
            self.fail("Should fail without arguments")
        except SystemExit:
            pass

    def test_main_invalid_args(self):
        sys.argv = ['paragres', '-c']

        try:
            cli.main()
            self.fail("Should fail with invalid argument")
        except SystemExit as e:
            self.assertEqual('0', str(e))

    @patch('subprocess.check_call')
    def test_main_success(self, mock_check_call):
        sys.argv = ['paragres', '-b', 'sourcedb', '-n', 'destdb']

        result = cli.main()

        self.assertEqual(0, result)
        expected = [
            call(['pg_dump', '-Fc', '--no-acl', '--no-owner', '--dbname=sourcedb',
                  StringStartsWith('--file=sourcedb-backup-')]),
            call(['dropdb', '--if-exists', 'destdb']),
            call(['createdb', 'destdb']),
            call(['pg_restore', '--no-acl', '--no-owner', '--dbname=destdb',
                  StringStartsWith('sourcedb-backup-')])
        ]
        self.assertEqual(expected, mock_check_call.call_args_list)
