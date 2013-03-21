from contextlib import contextmanager
from email.parser import Parser
from getpass import getpass
import logging
from pprint import pprint

import argh
from argh import arg
import arghlog
from imapclient import IMAPClient
from prettytable import PrettyTable


@contextmanager
def folder(server, foldername, readonly=False):
    server.select_folder(foldername, readonly=readonly)
    try:
        yield
    finally:
        server.close_folder()


@contextmanager
def connect(host, no_ssl=False):
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

    use_ssl = not no_ssl
    server = IMAPClient(host, port, ssl=use_ssl)
    server.normalise_times = False
    server.login(username, password)
    yield server
    server.logout()


class CommandSet(set):
    def __call__(self, fn):
        self.add(fn)

cmd = CommandSet()


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('--no-ssl', help='connect without SSL')
def login(host, no_ssl=False):
    """Test that a server is reachable and try to log in."""
    with connect(host, no_ssl) as server:
        logging.info("Connected successfully")
        logging.debug("Server capabilities: %r", server.capabilities())


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('--no-ssl', help='connect without SSL')
def folders(host, no_ssl=False):
    """List available mail folders."""
    with connect(host, no_ssl) as server:
        folders = server.list_folders()

        table = PrettyTable(['Name', 'Flags', 'Delimiter', 'Messages', 'Unread'])
        for flags, delimiter, name in sorted(folders, key=lambda f: f[2]):
            status = server.folder_status(name, ['MESSAGES', 'UNSEEN'])
            table.add_row([name, ' '.join(flags), delimiter, status['MESSAGES'], status['UNSEEN']])
        print table


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('folder', help='name of the folder to list')
@arg('--no-ssl', help='connect without SSL')
def messages(host, folder, no_ssl=False):
    """List messages in a folder."""
    with connect(host, no_ssl) as server:
        with folder(server, folder, readonly=True):
            message_ids = server.search()
            messages = server.fetch(message_ids, ['BODY.PEEK[HEADER]', 'INTERNALDATE', 'FLAGS'])

    table = PrettyTable(['#', 'From', 'Subject', 'Timestamp', 'Flags'])
    for message in messages.itervalues():
        headers = Parser().parsestr(message['BODY[HEADER]'])
        timestamp = message['INTERNALDATE'].isoformat()
        flags = ' '.join(message['FLAGS'])
        table.add_row([message['SEQ'], headers['from'], headers['subject'], timestamp, flags])
    print table


@cmd
@arg('from-host', help='server to copy messages from')
@arg('from-folder', help='folder on "from" server to copy messages from')
@arg('to-host', help='server to copy messages to')
@arg('to-folder', help='folder on "to" server to copy messages to')
@arg('--from-no-ssl', help='connect to "from" server without SSL')
@arg('--to-no-ssl', help='connect to "to" server without SSL')
def migrate(from_host, from_folder, to_host, to_folder, from_no_ssl=False, to_no_ssl=False):
    """Copy messages from one server to another."""
    with connect(from_host, from_no_ssl) as from_server:
        with folder(from_server, from_folder, readonly=True):
            message_ids = from_server.search()
            messages = from_server.fetch(message_ids, ['BODY.PEEK[]', 'INTERNALDATE', 'FLAGS'])

    logging.debug("Found %d messages, copying...", len(messages))

    with connect(to_host, to_no_ssl) as to_server:
        for message in messages.itervalues():
            # \Recent is a "read-only" flag so don't try to set it.
            flags = [flag for flag in message['FLAGS'] if flag.lower() != '\\recent']
            to_server.append(to_folder, message['BODY[]'], flags, message['INTERNALDATE'])
            logging.debug("appended message %r", message['SEQ'])

    logging.info("Copied %d messages", len(messages))


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('folder', help='name of the folder containing the message to show')
@arg('messageid', help='message ID of the message to show')
@arg('--no-ssl', help='connect without SSL')
def peek(host, folder, messageid, no_ssl=False):
    """Peek at a message."""
    with connect(host, no_ssl) as server:
        with folder(server, folder, readonly=True):
            messages = server.fetch([messageid], ['BODY.PEEK[]', 'INTERNALDATE', 'FLAGS'])
    for mid, message in messages.items():
        logging.debug("Message %r has keys %s", mid, ', '.join(message.keys()))
        body = message['BODY[]']
        timestamp = message['INTERNALDATE'].isoformat()
        flags = ' '.join(message['FLAGS'])

        print mid, timestamp, flags
        print body
        print


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('from-folder', help='folder to move messages from')
@arg('to-folder', help='folder to move messages to')
@arg('--no-ssl', help='connect without SSL')
def merge(host, from_folder, to_folder, no_ssl=False):
    """Merge a folder into another on one server.

    The folder from which messages are moved is left empty.

    """
    with connect(host, no_ssl) as server:
        with folder(server, from_folder):  # read-write
            message_ids = server.search()
            result = server.copy(message_ids, to_folder)
            logging.debug("Moved %d messages", len(message_ids))
            server.delete_messages(message_ids)
            server.expunge()

    logging.info("Moved %d messages from %s to %s", len(message_ids), from_folder, to_folder)


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('folder', help='name of the folder to create')
@arg('--no-ssl', help='connect without SSL')
def createfolder(host, folder, no_ssl=False):
    """Create a new mail folder."""
    with self.connect(host, no_ssl) as server:
        server.create_folder(folder)
    logging.info("Created!")


@cmd
@arg('host', help='hostname of the IMAP server')
@arg('folder', help='name of the folder to delete')
@arg('--yes', help='delete the folder even if it contains messages')
@arg('--no-ssl', help='connect without SSL')
def rmfolder(host, folder, yes=False, no_ssl=False):
    """Delete a mail folder."""
    with connect(host, no_ssl) as server:
        status = server.folder_status(folder, ['MESSAGES'])
        if status['MESSAGES'] > 0 and not yes:
            logging.error("Folder %s contains messages", folder)
            return

        server.delete_folder(folder)

    logging.info("Deleted %s with %d messages", folder, status['MESSAGES'])


if __name__ == '__main__':
    parser = argh.ArghParser()
    arghlog.add_logging(parser)
    parser.add_commands(cmd)
    parser.dispatch()
