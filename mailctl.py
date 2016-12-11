#!/usr/bin/env python
"""
mailctl.py

Helper script to manage Postfix mail aliases kept in a SQLite Database
"""

import sys
import os
import argparse
import sqlite3
try:
    from passlib.hash import sha512_crypt
except ImportError:
    print 'Failed to import passlib.'
    print 'Please run this script in a virtual environment with passlib installed'
    sys.exit(1)
from random import choice


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


class MailCtl(object):
    """
    Script main class
    """

    DB = 'mail.sqlite'

    def __init__(self):
        # Create top level parser
        parser = argparse.ArgumentParser(description='Postfix database management tool',
                usage='''mailctl.py <command> [<args>]

The most commonly used commands are:
   user     manage users
   alias    mange aliases
   domains  manage domains
''')
        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but exclude the rest of the args too,
        # or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print 'Unrecognized command'
            parser.print_help()
            sys.exit(1)

        # Setup database connection
        if not os.path.isfile(self.DB):
            print 'Database file {} is not a file.'.format(self.DB)
            sys.exit(1)
        else:
            try:
                self.db = Database(self.DB)
            except sqlite3.OperationalError as error:
                print 'Failed to open database file {}: {}'.format(self.DB, str(error))
                sys.exit(1)

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def show_users(self):
        """
        Show database users
        """
        db_query = 'SELECT email FROM virtual_users'
        result = self.db.query(db_query)
        for row in result:
            print row[0]

    def add_user(self, username):
        """
        Addd user to database
        """

        # Check if user already exists before we add him twice
        db_query = "SELECT email FROM virtual_users WHERE email = '{}'".format(username)
        result = self.db.query(db_query)
        if result.fetchone():
            print 'User {} already exists!'.format(username)
            return False
        # Get id of virtual domain this user belongs to
        try:
            domain = username.split('@')[1]
        except IndexError:
            print 'Invalid user name syntax. Needs to be user@domain.tld.'
            return False
        db_query = "SELECT id FROM virtual_domains WHERE name = '{}'".format(domain)
        result = self.db.query(db_query)
        try:
            domain_id = result.fetchone()[0]
        except TypeError:
            print 'Domain {} is not handled by this system. Aborting.'.format(domain)
            return False

        # Create SHA512-Crypt password hash for this user
        charsets = [
            'abcdefghijklmnopqrstuvwxyz',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            '0123456789',
            '^!%&/()=?{[]}+~#-_.:,;<>',]
        password_characters = []
        charset = choice(charsets)
        while len(password_characters) < 12:
            password_characters.append(choice(charset))
            charset = choice(list(set(charsets) - set([charset])))
        password = "".join(password_characters)
        password_hash = '{SHA512-CRYPT}' + sha512_crypt.using(rounds=5000).hash(password)

        # Add user to database
        db_query = "INSERT INTO virtual_users "\
                   "(domain_id, password, email) VALUES ("\
                   "'{domain_id}', '{password}', '{user}')".format(
                        user=username,
                        password=password_hash,
                        domain_id=domain_id)
        result = self.db.query(db_query)
        if result.rowcount:
            print 'Added user {} with password {}'.format(username, password)
            return True
        else:
            print 'Failed to add user {} '.format(username)
            return False

    def delete_user(self, username):
        """
        Delete user from database
        """

        # Check if user to be deleted exists in database
        db_query = "SELECT email FROM virtual_users WHERE email = '{}'".format(username)
        result = self.db.query(db_query)
        if not result.fetchone():
            print 'User {} does not exist!'.format(username)
            return False

        # Get list of aliases pointing to this user
        db_query = "SELECT source FROM virtual_aliases WHERE destination = '{}'".format(username)
        result = self.db.query(db_query)
        result_set = result.fetchall()
        if result_set:
            aliases = []
            print 'User {} is configured destination for these virtual aliases.'.format(username)
            print 'They will be deleted along with the user!'
            for row in result_set:
                aliases.append("'{}'".format(row[0]))
                print row[0]
            prompt = 'Enter YES to confirm deletion of user {} and all of its aliases: '\
                     .format(username)
        else:
            print 'No virtual aliases configured for user {}'.format(username)
            prompt = 'Enter YES to confirm deletion of user {}: '.format(username)
        confirmation = raw_input(prompt)
        if confirmation != 'YES':
            print 'Aborting'
            return True

        # Delete virtual aliases for this user
        if aliases:
            db_query = "DELETE FROM virtual_aliases "\
                       "WHERE source IN ({aliases}) AND destination = '{user}'"\
                       .format(aliases=','.join(aliases),
                               user=username)
            result = self.db.query(db_query)
            if result.rowcount:
                print "Deleted virtual aliases for " + username
            else:
                print "Failed to delete virtual aliases for " + username
                return False

        # Delete user
        db_query = "DELETE FROM virtual_users WHERE email = '{}'".format(username)
        result = self.db.query(db_query)
        if result.rowcount:
            print 'Deleted user {}'.format(username)
            return True
        else:
            print 'Failed to delete user {} '.format(username)
            return False

    def show_aliases(self, filter):
        """
        Show configured aliases
        """
        if filter == 'all':
            db_query = 'SELECT source, destination FROM virtual_aliases'
        elif filter == 'enabled':
            db_query = 'SELECT source, destination FROM virtual_aliases WHERE enabled'
        elif filter == 'disabled':
            db_query = 'SELECT source, destination FROM virtual_aliases WHERE enabled = 0'
        else:
            print 'Invalid filter: ' + filter
            return False
        result = self.db.query(db_query)
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

    def search_aliases(self, pattern):
        """
        Search configured aliases
        """
        db_query = "SELECT source, destination FROM virtual_aliases "\
                   "WHERE source LIKE '%{}%'".format(pattern)
        result = self.db.query(db_query)
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

    def disable_alias(self, alias):
        """
        Disable virtual alias
        """

        db_query = "SELECT source FROM virtual_aliases "\
                   "WHERE enabled AND source = '{}'".format(alias)
        result = self.db.query(db_query)
        result_items = result.fetchone()
        if result_items is None:
            print 'No enabled alias {}!'.format(alias)
            return False
        db_query = "UPDATE virtual_aliases SET enabled = 0 "\
                   "WHERE source = '{}'".format(alias)
        result = self.db.query(db_query)
        if result.rowcount:
            print "Disabled virtual alias " + alias
            return True
        else:
            print "Failed to disable virtual alias " + alias
            return False

    def enable_alias(self, alias):
        """
        Enable virtual alias
        """

        db_query = "SELECT source FROM virtual_aliases "\
                   "WHERE enabled = 0 AND source = '{}'".format(alias)
        result = self.db.query(db_query)
        result_items = result.fetchone()
        if result_items is None:
            print 'No disabled alias {}!'.format(alias)
            return False
        db_query = "UPDATE virtual_aliases SET enabled = 1 "\
                   "WHERE source = '{}'".format(alias)
        result = self.db.query(db_query)
        if result.rowcount:
            print 'Enabled virtual alias ' + alias
            return True
        else:
            print 'Failed to enable virtual alias ' + alias
            return False

    def add_alias(self, alias, user, description):
        """
        Add virtual alias
        """

        db_query = "SELECT source, destination FROM virtual_aliases "\
                   "WHERE source = '{}' "\
                   "AND destination = '{}'".format(alias, user)
        result = self.db.query(db_query)
        result_items = result.fetchone()
        if result_items:
            print 'Alias {} -> {} already exists!'.format(alias, user)
            return False
        alias_domain = alias.split("@")[-1]
        # Check sanity of desired alias record
        db_query = "SELECT email FROM virtual_users WHERE email = '{}'".format(user)
        result = self.db.query(db_query)
        result_items = result.fetchone()
        if not result_items:
            print "Invalid user " + user
            return False
        db_query = "SELECT name FROM virtual_domains WHERE name = '{}'".format(alias_domain)
        result = self.db.query(db_query)
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
        result = self.db.query(db_query)
        if result.rowcount:
            print 'Added virtual alias {} -> {} '.format(alias, user)
            return True
        else:
            print 'Failed to add virtual alias {} -> {} '.format(alias, user)
            return False

    def delete_alias(self, alias):
        """
        Delete virtual alias from database
        """

        db_query = "SELECT source FROM virtual_aliases WHERE source = '{}'".format(alias)
        result = self.db.query(db_query)
        result_items = result.fetchone()
        if result_items is None:
            print 'Alias {} does not exist!'.format(alias)
            return False
        db_query = "DELETE FROM virtual_aliases WHERE source = '{}'".format(alias)
        result = self.db.query(db_query)
        if result.rowcount:
            print "Deleted virtual alias " + alias
            return True
        else:
            print "Failed to delete virtual alias " + alias
            return False

    def user(self):
        """
        Handle mail accounts
        """
        # Create command parser
        parser = argparse.ArgumentParser(
            description='Manage users')
        subparsers = parser.add_subparsers(dest='subcommand',
                                           title='subcommands',
                                           description='valid subcommands',
                                           help='valid subcommands')
        # Create subparsers
        parser_show = subparsers.add_parser('show', help='show users')
        parser_add = subparsers.add_parser('add', help='add user')
        parser_add.add_argument('username', help='user name')
        parser_delete = subparsers.add_parser('delete', help='delete user')
        parser_delete.add_argument('username', help='user name')

        args = parser.parse_args(sys.argv[2:])

        if args.subcommand == 'show':
            self.show_users()
        elif args.subcommand == 'add':
            if not self.add_user(args.username):
                sys.exit(1)
        elif args.subcommand == 'delete':
            if not self.delete_user(args.username):
                sys.exit(1)

    def alias(self):
        """
        Handle aliases
        """
        # Create command parser
        parser = argparse.ArgumentParser(
            description='Manage aliases')
        subparsers = parser.add_subparsers(dest='subcommand',
                                           title='subcommands',
                                           description='valid subcommands',
                                           help='valid subcommands')
        # Create parser for the "show" command
        parser_show = subparsers.add_parser('show', help='show aliases')
        parser_show.add_argument('-f', '--filter',
                                 help='filter alias',
                                 choices=['all', 'enabled', 'disabled'],
                                 default='all')
        # Create parser for the "search" command
        parser_search = subparsers.add_parser('search', help='search aliases')
        parser_search.add_argument('pattern', help='search pattern')
        # Create parser for the "disable" command
        parser_disable = subparsers.add_parser('disable', help='disable alias')
        parser_disable.add_argument('alias', help='alias to disable')
        # Create parser for the "disable" command
        parser_enable = subparsers.add_parser('enable', help='enable alias')
        parser_enable.add_argument('alias', help='alias to enable')
        # Create parser for the "add" command
        parser_add = subparsers.add_parser('add', help='add alias')
        parser_add.add_argument('-a', '--alias', help='alias name', required=True)
        parser_add.add_argument('-u', '--user', help='destination user', required=True)
        parser_add.add_argument('-c', '--comment',
                                help='alias description',
                                default='')
        # Create parser for the "delete" command
        parser_delete = subparsers.add_parser('delete', help='delete alias')
        parser_delete.add_argument('alias', help='alias to delete')

        args = parser.parse_args(sys.argv[2:])

        if args.subcommand == 'show':
            self.show_aliases(args.filter)
        elif args.subcommand == 'search':
            self.search_aliases(args.pattern)
        elif args.subcommand == 'enable':
            if not self.enable_alias(args.alias):
                sys.exit(1)
        elif args.subcommand == 'disable':
            if not self.disable_alias(args.alias):
                sys.exit(1)
        elif args.subcommand == 'add':
            if not self.add_alias(args.alias, args.user, args.comment):
                sys.exit(1)
        elif args.subcommand == 'delete':
            if not self.delete_alias(args.alias):
                sys.exit(1)


if __name__ == '__main__':
    MailCtl()
