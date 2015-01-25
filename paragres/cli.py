import argparse

from paragres.command import Command


def create_parser():
    parser = argparse.ArgumentParser(
        description='Copy a PostgreSQL database from one location to another.\n'
                    'Any Heroku apps must have the Heroku Postgres and PG Backups add-ons.\n'
                    'Specify a Heroku app destination with -d or omit to use localhost.\n'
                    'A single source is required, one of (-l, -u, -s) for a Heroku destination '
                    'or one of (-f, -l, -u, -s) for the localhost destination.\n'
                    'The localhost destination requires either a settings file (-t) or a database '
                    'name (-n). If authentication parameters are not supplied in a settings file, '
                    'standard PostgreSQL authentication will apply.')
    parser.add_argument('-f', '--file', type=str,
                        help='PostgreSQL dump file to use as a data source')
    parser.add_argument('-l', '--local-db', type=str, help='Local dbname to use as a data source')
    parser.add_argument('-u', '--url', type=str, help='Public URL from which to pull db file')
    parser.add_argument('-s', '--source-app', type=str, help='Heroku app from which to pull db')
    parser.add_argument('-d', '--destination-app', type=str,
                        help='Heroku app for which to replace db')
    parser.add_argument('-n', '--dbname', type=str, help='Database name on localhost')
    parser.add_argument('-t', '--settings', type=str,
                        help="Django-style settings file with database connection information, or "
                             "'DJANGO_SETTINGS_MODULE' to use that environment variable's value")
    parser.add_argument('-v', '--verbosity', type=int, default=1,
                        help='Verbosity level: 0=minimal output, 1=normal output')
    return parser


def error(parser, message):
        parser.print_help()
        parser.exit(message="\nERROR: %s\n" % message)


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.destination_app:
        has_one_data_source = (bool(args.local_db) ^ bool(args.url) ^ bool(args.source_app))
        if not has_one_data_source:
            error(parser, 'Heroku app destinations require a single source, one of '
                          'local database (-l), url (-u) or Heroku app (-s)')

    if not args.destination_app:
        if not args.settings and not args.dbname:
            error(parser, 'The localhost destination requires either a database name (-n) '
                          'or a settings file containing one (-t)\n')

        has_one_data_source = (bool(args.local_db) ^ bool(args.file) ^ bool(args.url)
                               ^ bool(args.source_app))
        if not has_one_data_source:
            error(parser, 'The localhost destination requires a single source, one of '
                          'file (-f), local database (-l), url (-u), or Heroku app (-s)')

    command = Command(args)
    command.run()
