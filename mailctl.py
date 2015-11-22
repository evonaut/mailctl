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


def disable_alias(database, alias):
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


def enable_alias(database, alias):
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
        print 'Enabled virtual alias ' + alias
        return True
    else:
        print 'Failed to enable virtual alias ' + alias
        return False


def add_alias(database, alias, user, description):
    """
    Add virtual alias
    """

    db = Database(database)
    db_query = "SELECT source, destination FROM virtual_aliases "\
               "WHERE source = '{}' "\
               "AND destination = '{}'".format(alias, user)
    result = db.query(db_query)
    result_items = result.fetchone()
    if result_items:
        print 'Alias {} -> {} already exists!'.format(alias, user)
        return False
    alias_domain = alias.split("@")[-1]
    # Check sanity of desired alias record
    db_query = "SELECT email FROM virtual_users WHERE email = '{}'".format(user)
    result = db.query(db_query)
    result_items = result.fetchone()
    if not result_items:
        print "Invalid user " + user
        return False
    db_query = "SELECT name FROM virtual_domains WHERE name = '{}'".format(
        alias_domain)
    result = db.query(db_query)
    result_items = result.fetchone()
    if not result_items:
        print '{} is not a domain managed by this server!'.format(alias_domain)
        return False
    # Finally add alias
    db_query = "INSERT INTO virtual_aliases "\
               "(source,destination,description,domain_id) VALUES ("\
               "'{source}', '{destination}', '{description}', "\
               "(SELECT id from virtual_domains WHERE name='{domain}'))"\
               .format(
                    source=alias,
                    destination=user,
                    description=description,
                    domain=alias_domain)
    result = db.query(db_query)
    if result.rowcount:
        print 'Added virtual alias {} -> {} '.format(alias, user)
        return True
    else:
        print 'Failed to add virtual alias {} -> {} '.format(alias, user)
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
                             help='show database content',
                             choices=['users',
                                      'domains',
                                      'aliases',
                                      'disabled'])
    # Create parser for the "disable" command
    parser_disable = subparsers.add_parser('disable', help='disable alias')
    parser_disable.add_argument('alias', help='alias to disable')
    # Create parser for the "disable" command
    parser_enable = subparsers.add_parser('enable', help='enable alias')
    parser_enable.add_argument('alias', help='alias to enable')
    # Create parser for the "add" command
    parser_add = subparsers.add_parser('add', help='add alias')
    parser_add.add_argument('-a', '--alias', help='alias name')
    parser_add.add_argument('-u', '--user', help='destination user')
    parser_add.add_argument('-c', '--comment',
                            help='alias description',
                            default='')
    # Parse provided arguments
    args = parser.parse_args()
    if not os.path.isfile(args.database):
        print 'Database file {} does not exist!'.format(args.database)
        sys.exit(1)
    if args.subcommand == 'show':
        show(args.database, args.objects)
    elif args.subcommand == 'disable':
        disable_alias(args.database, args.alias)
    elif args.subcommand == 'enable':
        enable_alias(args.database, args.alias)
    elif args.subcommand == 'add':
        add_alias(args.database, args.alias, args.user, args.comment)


if __name__ == '__main__':
    main()
