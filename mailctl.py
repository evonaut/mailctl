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
    if objects in ('aliases', 'disabled'):
        if objects == 'aliases':
            db_query = 'SELECT source, destination, created, description '\
                       'FROM virtual_aliases WHERE enabled'
        else:
            db_query = 'SELECT source, destination, created, description '\
                       'FROM virtual_aliases WHERE enabled = 0'
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
        return True
    elif objects == 'domains':
        db_query = 'SELECT name FROM virtual_domains'
    elif objects == 'users':
        db_query = 'SELECT email FROM virtual_users'
    else:
        print 'Invalid object type to show'
        return False
    result = db.query(db_query)
    for row in result:
        print row[0]
    return True


def disable(database, alias):
    """
    Disable virtual alias
    """

    db = Database(database)
    db_query = "SELECT source FROM virtual_aliases "\
               "WHERE enabled AND source = '{}'".format(alias)
    result = db.query(db_query)
    result_items = result.fetchone()
    if result_items is None:
        print 'No enabled alias {}!'.format(alias)
        return False
    db_query = "UPDATE virtual_aliases SET enabled = 0 "\
               "WHERE source = '{}'".format(alias)
    result = db.query(db_query)
    if result.rowcount:
        print "Disabled virtual alias " + alias
        return True
    else:
        print "Failed to disable virtual alias " + alias
        return False


def enable(database, alias):
    """
    Enable virtual alias
    """

    db = Database(database)
    db_query = "SELECT source FROM virtual_aliases "\
               "WHERE enabled = 0 AND source = '{}'".format(alias)
    result = db.query(db_query)
    result_items = result.fetchone()
    if result_items is None:
        print 'No disabled alias {}!'.format(alias)
        return False
    db_query = "UPDATE virtual_aliases SET enabled = 1 "\
               "WHERE source = '{}'".format(alias)
    result = db.query(db_query)
    if result.rowcount:
        print "Enabled virtual alias " + alias
        return True
    else:
        print "Failed to enable virtual alias " + alias
        return False


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
    # Create parser for the "show" command
    parser_show = subparsers.add_parser('show',
                                        help='show database content')
    parser_show.add_argument('objects',
                             help='show users',
                             choices=['users',
                                      'domains',
                                      'aliases',
                                      'disabled'])
    # Create parser for the "disable" command
    parser_disable = subparsers.add_parser('disable', help='disable alias')
    parser_disable.add_argument('alias', help='alias to disable')
    # Create parser for the "disable" command
    parser_disable = subparsers.add_parser('enable', help='enable alias')
    parser_disable.add_argument('alias', help='alias to ensable')
    # Parse provided arguments
    args = parser.parse_args()
    if not os.path.isfile(args.database):
        print 'Database file {} does not exist!'.format(args.database)
        sys.exit(1)
    if args.subcommand == 'show':
        show(args.database, args.objects)
    elif args.subcommand == 'disable':
        disable(args.database, args.alias)
    elif args.subcommand == 'enable':
        enable(args.database, args.alias)


if __name__ == '__main__':
    main()
