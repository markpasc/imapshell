#!/usr/bin/env python

from getpass import getpass
import imaplib
import logging

from termtool import Termtool, argument, subcommand


class Imapshell(Termtool):

    def connect(self, host, use_ssl=True, port=None, username=None):
        cls = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
        if port is None:
            conn = cls(host)
        else:
            conn = cls(host, port)

        if 'AUTH=CRAM-MD5' in conn.capabilities:
            login_method = conn.login_cram_md5
        elif not use_ssl:
            raise ValueError("Won't use plaintext login without SSL")
        else:
            login_method = conn.login

        if username is None:
            username = raw_input(host + " login name: ")
        password = getpass(host + " password: ")
        login_method(username, password)

        return conn

    @subcommand(help='test that a server is reachable and try to log in')
    @argument('host', help='hostname of the IMAP server')
    @argument('--port', type=int, default=None, help='port at which to connect to the server')
    @argument('--user', help='name to log in with')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def login(self, args):
        conn = self.connect(args.host, args.ssl, args.port, args.user)
        logging.info("Connected successfully")
        logging.debug("Server capabilities: %r", conn.capabilities)


if __name__ == '__main__':
    Imapshell().run()
