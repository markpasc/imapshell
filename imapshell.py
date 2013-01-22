#!/usr/bin/env python

from getpass import getpass
from imapclient import IMAPClient
import logging

from termtool import Termtool, argument, subcommand


class Imapshell(Termtool):

    def connect(self, host, use_ssl=True):
        if '@' in host:
            # Split from the end in case the username is an email address.
            username, host = host.rsplit('@', 1)
        else:
            username = raw_input(host + " login name: ")

        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)
        else:
            port = None

        password = getpass(host + " password: ")

        server = IMAPClient(host, port, ssl=use_ssl)
        server.login(username, password)
        return server

    @subcommand(help='test that a server is reachable and try to log in')
    @argument('host', help='hostname of the IMAP server')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def login(self, args):
        server = self.connect(args.host, args.ssl)
        logging.info("Connected successfully")
        logging.debug("Server capabilities: %r", conn.capabilities())


if __name__ == '__main__':
    Imapshell().run()
