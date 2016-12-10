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

DB = 'mail.sqlite'


class MailCtl(object):
    """
    Script main class
    """

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
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

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

        args = parser.parse_args(sys.argv[2:])

        if not os.path.isfile(DB):
            print 'Database file {} does not exist!'.format(DB)
            sys.exit(1)
        else:
            db = Database(DB)

        if args.subcommand == 'show':
            db_query = 'SELECT email FROM virtual_users'
            result = db.query(db_query)
            for row in result:
                print row[0]
            sys.exit(0)

        elif args.subcommand == 'add':
            # Check if user already exists before we add him twice
            db_query = "SELECT email FROM virtual_users WHERE email = '{}'".format(args.username)
            result = db.query(db_query)
            if result.fetchone():
                print 'User {} already exists!'.format(args.username)
                sys.exit(1)
            # Get id of virtual domain this user belongs to
            try:
                domain = args.username.split('@')[1]
            except IndexError:
                print 'Invalid user name syntax. Needs to be user@domain.tld.'
                sys.exit(1)
            db_query = "SELECT id FROM virtual_domains WHERE name = '{}'".format(domain)
            result = db.query(db_query)
            try:
                domain_id = result.fetchone()[0]
            except TypeError:
                print 'Domain {} is not handled by this system. Aborting.'.format(domain)
                sys.exit(1)

            # Create SHA512-Crypt password hash for this user
            charsets = [
                'abcdefghijklmnopqrstuvwxyz',
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                '0123456789',
                '^!\$%&/()=?{[]}+~#-_.:,;<>',]
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
                            user=args.username,
                            password=password_hash,
                            domain_id=domain_id)
            result = db.query(db_query)
            if result.rowcount:
                print 'Added user {} with password {}'.format(args.username, password)
                sys.exit(0)
            else:
                print 'Failed to add user {} '.format(args.username)
                sys.exit(1)

        elif args.subcommand == 'delete':
            print 'Deleting users is not implemented yet'
            sys.exit(0)


if __name__ == '__main__':
    MailCtl()
