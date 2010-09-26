#!/usr/bin/env python

import socket
import select
import re
import ConfigParser
from StringIO import StringIO
from textwrap import wrap

class MultiplexClientException(Exception):
    pass

class MultiplexClient(object):
    default_config = """
    [%s]
    port=9001
    password=
    socket_type=AF_UNIX
    listen_addr=multiplexserver.sock
    """
    _config_name = 'multiplexclient'

    def __init__(self, config=None):
        self.default_config = self.__class__.default_config % \
            self.__class__._config_name
        if config is None:
            self.load_config(self.default_config)
        else:
            self.load_config(config)
        self.running = False
            
    def __del__(self):
        if self.running:
            self.stop()

    def start(self):
        self.running = True
        self._init_socket()
        self._connect()
        self._run()

    def stop(self):
        self._disconnect()
        self.running = False

    def send_command(self, command):
        self.socket.send(command.encode('utf-8') + '\n')

    def dispatch_event(self, line):
        pass

    def _run(self):
        keep_running = True
        while keep_running:
            try:
                outset, inset, errset = select.select([self.socket],
                    [],
                    [self.socket])
            except select.error, error:
                raise MultiplexClientException(error)
            if self.socket in errset:
                raise MultiplexClientException('client in errset')
            elif self.socket in outset:
                self.dispatch_event(self._receive())

    def _init_socket(self):
        self.socket = socket.socket(self.config[self._config_name]['socket_type'],
            socket.SOCK_STREAM)
        self.socket_fd = self.socket.makefile()

    def _connect(self):
        try:
            if self.config[self._config_name]['socket_type'] == 'AF_UNIX':
                self.socket.connect(self.config[self._config_name]['listen_addr'])
            else:
                self.socket.connect((self.config[self._config_name]['listen_addr'],
                    self.config[self._config_name['port']]))
        except socket.error, error:
            raise MultiplexClientException(error)

        password_line = self.receive()
        if password_line.startswith('-'):
            self.send_command(self.config[self._config_name]['password'])
            reply = self.receive()
            if reply.startswith('-'):
                raise MultiplexClientException('bad password')

    def _disconnect(self):
        self.send_command('.close')
        while not self.receive().startswith('+'):
            pass
        self.socket.close()

    def _receive(self):
        buffer = self.socket_fd.readline()
        if not buffer:
            raise MultiplexClientException('empty buffer')
        return buffer.decode('utf-8').rstrip()

    def load_config(self, config):
        self.config = {}
        parser = ConfigParser.ConfigParser()
        if isinstance(config, basestring):
            if os.path.isfile(config):
                parser.read(config)
            else:
                parser.readfp(StringIO(config))
        elif isinstance(config, file):
            parser.readfp(config)
        else:
            raise MultiplexClientException('Couldn\'t find parser for config')

        self.config = {}
        for section in parser.sections():
            items = parser.items(section)
            self.config[section] = dict(zip(
                [item[0] for item in items],
                [item[1] for item in items]))

    def check_config(self):
        pass

    def save_config(self):
        pass

    def say(self, message, no_wrap=False):
        line_width = 44
        message = wrap(
            message,
            width=line_width,
            subsequent_indent='  ')
        for line in message:
            self.send_command('say %s' % line)

    def kick(self, target):
        if not isinstance(target, list):
            target = [target,]
        map(self.send_command, ['kick %s' % player for player in filter(
            lambda player: player in self.query_players(), target)])

    def ban(self, target):
        if not isinstance(target, list):
            target = [target,]
        map(self.send_command, ['ban %s' % player for player in filter(
            lambda player: player in self.query_players(), target)])

    def unban(self, target):
        if not isinstance(target, list):
            target = [target,]
        map(self.send_command, ['pardon %s' % player for player in filter(
            lambda player: player in self.query_players(), target)])

    def give(self, player, item, quantity=1):
        stack_size = 64
        stacks, remainder = divmod(quantity, stack_size)
        for stack in range(stacks):
            self.send_command('give %s %i %i' % (player, item, stack_size))
        if remainder is not 0:
            self.send_command('give %s %i %i' % (player, item, remainder))

    def tell(self, target, message):
        line_width = 44
        message = wrap(
            message,
            width=line_width,
            subsequent_indent='  ')
        if not isinstance(target, list):
            target = [target,]
        for player in target:
            for line in message:
                self.send_command('tell %s %s' % (player, line))

if __name__ == '__main__':
    import sys
    client = MultiplexClient(sys.argv[1])
    client.start()