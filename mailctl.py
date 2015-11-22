#!/usr/bin/env python
"""
mailctl.py

Helper script to manage Postfix mail aliases kept in a SQLite Database
"""

import sys
import os
import argparse
import sqlite3

DEFAULT_DB = '/etc/mail/mail.sqlite'


class Database(object):
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self.conn.execute('pragma foreign_keys = on')
        self.conn.commit()
        self.cur = self.conn.cursor()

    def query(self, arg):
        self.cur.execute(arg)
        self.conn.commit()
        return self.cur

    def __del__(self):
        self.conn.close()


def show(database, objects):
    """
    Show database content

    Valid show objects are users, domains and aliases
    """

    db = Database(database)
    if objects == 'aliases':
        db_query = 'SELECT source, destination, created, description '\
                   'FROM virtual_aliases WHERE enabled'
        result = db.query(db_query)
        aliases = {}
        for row in result:
            source = row[0]
            destination = row[1]
            if source in aliases.keys():
                aliases[source] = '{}, {}'.format(aliases[source], destination)
            else:
                aliases[source] = destination
        for alias in aliases:
            print '{} -> {}'.format(alias, aliases[alias])


def main():
    """
    Script main routine
    """
    # Setup argument parser
    # Create top level parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database',
                        help='database to use',
                        default=DEFAULT_DB)
    subparsers = parser.add_subparsers(dest='subcommand',
                                       title='subcommands',
                                       description='valid subcommands',
                                       help='sub-command help')
    # Create parser for the "show" command"
    parser_show = subparsers.add_parser('show',
                                        help='show database content')
    parser_show.add_argument('objects',
                             help='show users',
                             choices=['users', 'domains', 'aliases'])
    # Parse provided arguments
    args = parser.parse_args()
    if not os.path.isfile(args.database):
        print 'Database file {} does not exist!'.format(args.database)
        sys.exit(1)
    if args.subcommand == 'show':
        show(args.database, args.objects)


if __name__ == '__main__':
    main()
