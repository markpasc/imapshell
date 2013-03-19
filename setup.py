from setuptools import setup

setup(
    name='imapshell',
    version='1.0',
    description='Debug and migrate IMAP accounts from the command line',
    scripts=['bin/imapshell'],
    py_modules=['imapshell'],
    requires=['IMAPClient', 'termtool', 'progressbar', 'PrettyTable'],
    install_requires=['IMAPClient', 'termtool', 'progressbar', 'PrettyTable'],
)
