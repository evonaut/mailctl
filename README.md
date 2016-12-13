# mailctl
Tool to manage virtual domains, users and aliases used by [Postfix](http://www.postfix.org)
and [Dovecot](https://www.dovecot.org) in a [SQLite](https://sqlite.org) database.

## Why?
When I migrated my Postfix configuration to use a SQLite database instead of plain text files
for domains, users and aliases, there were plenty of resources that described how to configure
Postfix and Dovecot for that, but a practical way to manage the data in this mail database
was left to the user. Using SQL queries in the SQLite CLI might be a way for some of us, but 
it's far from convenient and fails to create the required password hashes. So I started to 
write the missing tool myself. Hello `mailctl.py`.

## Requirements
`mailctl` requires a Python 2 interpreter to run. This implementation relies on the database
schema I use for my personal setup (available in`contrib/db_schema.sql`) but can be adjusted
to other database designs as well. Config snippets to make this work with Postfix and Dovecot
are included. I'm sure it can be used for other mail transfer agents or IMAP servers but I
haven't tested that.

Creation of user password hashes relies on the Python
[passlib](https://pypi.python.org/pypi/passlib) module which is not part of the standard Python
distribution. The script can be used without it, but then users can not be added and their
passwords can not be changed. Currently all passwords will be hashed using SHA512-CRYPT.

The `passlib` module can be installed via your system's package manager
or [pip](https://pypi.python.org/pypi/pip):

* Install `passlib` on Debian: `apt install python-passlib`  
* Install `passlib` using pip: `pip install passlib`

## Usage
Domains, users and aliases can be managed using subcommands. A help system is included.

Examples:
```bash
# Add virtual domain sample.local
$ mailctl.py domain add sample.local
Added domain sample.local

# Add virtual user joe@sample.local
$ mailctl.py user add joe@sample.local
Added user joe@sample.local with password some_password

# Add some virtual aliases
$ mailctl.py alias add -a joe.sample@sample.local -u joe@sample.local
Added virtual alias joe.sample@sample.local -> joe@sample.local
$ mailctl.py alias add -a dreamteam@sample.local -u joe@sample.local
Added virtual alias dreamteam@sample.local -> joe@sample.local 
$ mailctl.py alias add -a dreamteam@sample.local -u jim@sample.local
Added virtual alias dreamteam@sample.local -> jim@sample.local  

# List the configured users
$ mailctl.py user show
joe@sample.local
jim@sample.local

# Search virtual aliases
$ mailctl.py alias search joe.
joe.sample@sample.local -> joe@sample.local
$ mailctl.py alias search dream
dreamteam@sample.local -> joe@sample.local, jim@sample.local
 
# Wipe the sample.local domain from our server
$ mailctl.py domain delete sample.local
Domain sample.local is home of these users. They will be deleted!
jim@sample.local
joe@sample.local
Domain sample.local is home of these aliases. They will be deleted!
dreamtean@sample.local
joe.sample@sample.local

Enter YES to remove domain sample.local including all aliases and users: YES
Deleted virtual aliases from sample.local
Deleted users from sample.local
Deleted domain sample.local
```