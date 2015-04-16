import argparse
import pkg_resources

from paragres.command import Command


def create_parser():
    parser = argparse.ArgumentParser(
        description='Copy a PostgreSQL database from one location to another.\n\n'
                    'Any Heroku apps must have the Heroku Postgres and PG Backups add-ons.\n'
                    'Specify a Heroku app destination with -d or omit to use postgres directly.\n\n'
                    'A single source is required, one of (-u, -s, -b, -o) for a Heroku destination'
                    '\nor one of (-f, -u, -s, -b, -o) for a postgres destination.\n'
                    'You may specify that a new Heroku backup be captured (-c), otherwise the '
                    'most recent backup will be used.\n\n'
                    'A postgres source requires either a settings file (-o) or a database '
                    'name (-b).\nA postgres destination also requires either a settings file (-t) '
                    'or a database name (-n).\nIf authentication parameters are not supplied in a '
                    'settings file, standard PostgreSQL authentication will apply.',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--version', action='store_true', default=False,
                        help="Show program's version number")
    parser.add_argument('-f', '--file', type=str,
                        help='PostgreSQL dump file to use as a data source')
    parser.add_argument('-u', '--url', type=str, help='Public URL from which to pull db file')
    parser.add_argument('-s', '--source-app', type=str, help='Heroku app from which to pull db')
    parser.add_argument('-c', '--capture', default=False, action='store_true',
                        help='Capture a new Heroku backup')
    parser.add_argument('-o', '--source-settings', type=str,
                        help="Django-style settings file with database connection information for "
                             "source database\n(or 'DJANGO_SETTINGS_MODULE' to use that "
                             "environment variable's value)")
    parser.add_argument('-b', '--source-dbname', type=str,
                        help='Source database name (overrides value in source settings if both are '
                             'specified)')
    parser.add_argument('-d', '--destination-app', type=str,
                        help='Heroku app for which to replace db')
    parser.add_argument('-t', '--settings', type=str,
                        help="Django-style settings file with database connection information for "
                             "destination database\n(or 'DJANGO_SETTINGS_MODULE' to use that "
                             "environment variable's value)")
    parser.add_argument('-n', '--dbname', type=str,
                        help='Destination database name (overrides value in settings if both are '
                             'specified)')
    parser.add_argument('-v', '--verbosity', type=int, default=1,
                        help='Verbosity level: 0=minimal output, 1=normal output')
    # The pgbackups addon is deprecated, but continue supporting it until it is removed
    parser.add_argument('--use-pgbackups', action='store_true', default=False,
                        help="Use the deprecated pgbackups addon rather than Heroku pg:backups")
    return parser


def verify_args(args):

    if args.capture and not args.source_app:
        return 'Heroku backup capture requires a source Heroku app (-s)'

    if args.destination_app:
        has_one_data_source = (bool(args.url) ^ bool(args.source_app)
                               ^ bool(args.source_dbname) ^ bool(args.source_settings))
        if not has_one_data_source:
            return ('A Heroku app destination requires a single source, one of url (-u), '
                    'Heroku app (-s), db name (-b) or db settings (-o)')
    else:
        if not args.dbname and not args.settings and not args.capture:
            # Capturing a db does not require any destination information, so it is ok not to have
            # any destination if capture is set
            return ('A postgres destination requires either a database name (-n) or a '
                    'settings file containing one (-t)')

        has_one_data_source = (bool(args.file) ^ bool(args.url) ^ bool(args.source_app)
                               ^ bool(args.source_dbname) ^ bool(args.source_settings))
        if not has_one_data_source:
            return ('A postgres destination requires a single source, one of file (-f), url (-u), '
                    'Heroku app (-s), db name (-b) or db settings (-o)')

    return None


def error(parser, message):
        parser.print_help()
        parser.exit(message="\nERROR: %s\n" % message)


def main():
    parser = create_parser()
    parsed_args = parser.parse_args()

    if parsed_args.version:
        parser.exit("paragres %s" % pkg_resources.require("paragres")[0].version)

    error_message = verify_args(parsed_args)
    if error_message:
        error(parser, error_message)
    command = Command(parsed_args)
    command.run()
    return 0
