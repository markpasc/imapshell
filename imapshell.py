#!/usr/bin/env python

from contextlib import contextmanager
from email.parser import Parser
from getpass import getpass
from imapclient import IMAPClient
import logging
from pprint import pprint

from termtool import Termtool, argument, subcommand


@contextmanager
def folder(server, foldername, readonly=False):
    server.select_folder(foldername, readonly=readonly)
    try:
        yield
    finally:
        server.close_folder()


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
        server.normalise_times = False
        server.login(username, password)
        return server

    @subcommand(help='test that a server is reachable and try to log in')
    @argument('host', help='hostname of the IMAP server')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def login(self, args):
        server = self.connect(args.host, args.ssl)
        logging.info("Connected successfully")
        logging.debug("Server capabilities: %r", conn.capabilities())

    @subcommand(help='list available mail folders')
    @argument('host', help='hostname of the IMAP server')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def folders(self, args):
        server = self.connect(args.host, args.ssl)
        folders = server.list_folders()

        table = self.table(['Name', 'Flags', 'Delimiter'])
        for flags, delimiter, name in folders:
            table.add_row([name, ' '.join(flags), delimiter])
        print table

    @subcommand(help='list mail in a mailbox')
    @argument('host', help='hostname of the IMAP server')
    @argument('box', help='name of the mailbox to open')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def list(self, args):
        server = self.connect(args.host, args.ssl)
        with folder(server, args.box, readonly=True):
            message_ids = server.search()
            messages = server.fetch(message_ids, ['BODY.PEEK[HEADER]', 'FLAGS'])

        table = self.table(['#', 'From', 'Subject', 'Flags'])
        for message in messages.itervalues():
            headers = Parser().parsestr(message['BODY[HEADER]'])
            table.add_row([message['SEQ'], headers['from'], headers['subject'], ' '.join(message['FLAGS'])])
        print table


if __name__ == '__main__':
    Imapshell().run()
