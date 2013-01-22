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

        table = self.table(['Name', 'Flags', 'Delimiter', 'Messages', 'Unread'])
        for flags, delimiter, name in folders:
            status = server.folder_status(name, ['MESSAGES', 'UNSEEN'])
            table.add_row([name, ' '.join(flags), delimiter, status['MESSAGES'], status['UNSEEN']])
        print table

    @subcommand(help='list messages in a folder')
    @argument('host', help='hostname of the IMAP server')
    @argument('folder', help='name of the folder to list')
    @argument('--no-ssl', action='store_false', dest='ssl', help='connect without SSL')
    def messages(self, args):
        server = self.connect(args.host, args.ssl)
        with folder(server, args.folder, readonly=True):
            message_ids = server.search()
            messages = server.fetch(message_ids, ['BODY.PEEK[HEADER]', 'INTERNALDATE', 'FLAGS'])

        table = self.table(['#', 'From', 'Subject', 'Timestamp', 'Flags'])
        for message in messages.itervalues():
            headers = Parser().parsestr(message['BODY[HEADER]'])
            timestamp = message['INTERNALDATE'].isoformat()
            flags = ' '.join(message['FLAGS'])
            table.add_row([message['SEQ'], headers['from'], headers['subject'], timestamp, flags])
        print table

    @subcommand(help='copy messages from one server to another')
    @argument('left_server', metavar='from', help='server to copy messages from')
    @argument('left_folder', metavar='from_folder', help='folder on "from" server to copy messages from')
    @argument('right_server', metavar='to', help='server to copy messages to')
    @argument('right_folder', metavar='to_folder', help='folder on "to" server to copy messages to')
    @argument('--from-no-ssl', action='store_false', dest='left_ssl', help='connect to "from" server without SSL')
    @argument('--to-no-ssl', action='store_false', dest='right_ssl', help='connect to "to" server without SSL')
    def copy(self, args):
        left_server = self.connect(args.left_server, args.left_ssl)
        with folder(left_server, args.left_folder, readonly=True):
            message_ids = left_server.search()
            messages = left_server.fetch(message_ids, ['BODY.PEEK[]', 'INTERNALDATE', 'FLAGS'])

        logging.debug("Found %d messages, copying...", len(messages))

        right_server = self.connect(args.right_server, args.right_ssl)
        for message in messages.itervalues():
            right_server.append(args.right_folder, message['BODY[]'], message['FLAGS'], message['INTERNALDATE'])
            logging.debug("appended message %r", message['SEQ'])

        logging.info("Copied %d messages", len(messages))


if __name__ == '__main__':
    Imapshell().run()
