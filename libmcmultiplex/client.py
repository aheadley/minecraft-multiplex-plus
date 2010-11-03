#!/usr/bin/env python

import socket
import select
import re
import ConfigParser
import os.path
from StringIO import StringIO
from textwrap import wrap

from events import EVENTS

class ClientException(Exception):
    pass

class ClientInvalidTargetException(ClientException):
    def __init__(self, player, message=None):
        self.target = target
        if message is not None:
            self.message = message
        else:
            self.message = 'not found or invalid'
    def __str__(self):
        return '%s %s.' % (self.target, self.message)

class Client(object):
    default_config = """
    [%s]
    port=9001
    password=
    socket_type=AF_UNIX
    listen_addr=multiplexserver.sock
    """
    _config_name = 'multiplexclient'

    _line_width = 44
    _stack_size = 64
    _say_wrap_indent = _tell_wrap_indent = '>>'

    def __init__(self, config=None):
        self.default_config = self.__class__.default_config % \
            self.__class__._config_name
        if config is None:
            self.load_config(self.default_config)
        else:
            self.load_config(config)
        self.running = False
        self.bootstrap()

    def bootstrap(self):
        self.players = {}
        self.ops = []
        self.banned_players = []
        self.banned_ips = []

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
        line = line.strip()
        for event in EVENTS:
            if isinstance(EVENTS[event], list):
                break_ = False
                for event_pattern in EVENTS[event]:
                    match = event_pattern.match(line)
                    if match:
                        try:
                            getattr(self, 'on_%s' % event)(**match.groupdict())
                        except AttributeError:
                            pass
                        break_ = True
                        break
                if break_:
                    break
            else:
                match = EVENTS[event].match(line)
                if match:
                    try:
                        getattr(self, 'on_%s' % event)(**match.groupdict())
                    except AttributeError:
                        pass
                    break
        try:
            self.on_raw(line)
        except AttributeError:
            pass
                
    def _run(self):
        keep_running = True
        while keep_running:
            try:
                outset, inset, errset = select.select([self.socket],
                    [],
                    [self.socket])
            except select.error, error:
                raise ClientException(error)
            if self.socket in errset:
                raise ClientException('Client in errset')
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
            raise ClientException(error)

        password_line = self.receive()
        if password_line.startswith('-'):
            self.send_command(self.config[self._config_name]['password'])
            reply = self.receive()
            if reply.startswith('-'):
                raise ClientException('Bad password.')

    def _disconnect(self):
        self.send_command('.close')
        while not self.receive().startswith('+'):
            pass
        self.socket.close()

    def _receive(self):
        buffer = self.socket_fd.readline()
        if not buffer:
            raise ClientException('Empty buffer.')
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
            raise ClientException('Couldn\'t find parser for config')

        self.config = {}
        for section in parser.sections():
            items = parser.items(section)
            self.config[section] = dict(zip(
                [item[0] for item in items],
                [item[1] for item in items]))

    def say(self, message, no_wrap=False):
        if no_wrap:
            self.send_command('say %s' % message)
        else:
            message = wrap(
                message,
                width=self._line_width,
                subsequent_indent=self._say_wrap_indent)
            for line in message:
                self.send_command('say %s' % line)

    def kick(self, target):
        if target.lower() not in self.players:
            raise ClientInvalidTargetException(target)
        else:
            self.send_command('kick %s' % target)

    def ban(self, target):
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', target.strip()):
            self._ban_ip(target)
        else:
            self._ban_player(target)

    def _ban_player(self, player):
        if player.lower() in self.banned_players:
            raise ClientInvalidTargetException(player, 'is already banned')
        else:
            self.send_command('ban %s' % player)

    def _ban_ip(self, ip):
        if ip in self.banned_ips:
            raise ClientInvalidTargetException(ip, 'is already banned')
        else:
            self.send_command('ban-ip %s' % ip)

    def unban(self, target):
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', target.strip()):
            self._unban_ip(target)
        else:
            self._unban_player(target)

    def _unban_player(self, player):
        if player.lower() not in self.banned_players:
            raise ClientInvalidTargetException(player, 'is not banned')
        else:
            self.send_command('pardon %s' % player)

    def _unban_ip(self, ip):
        if ip not in self.banned_ips:
            raise ClientInvalidTargetException(ip, 'is not banned')
        else:
            self.send_command('pardon-ip %s' % ip)

    def op(self, player):
        if player in self.ops:
            raise ClientInvalidTargetException(player, 'is already an op')
        else:
            self.send_command('op %s' % player)

    def deop(self, player):
        if player not in self.ops:
            raise ClientInvalidTargetException(player, 'is not an op')
        else:
            self.send_command('deop %s' % player)

    def give(self, player, item, quantity=1):
        stacks, remainder = divmod(quantity, self._stack_size)
        if player.lower() not in self.players:
            raise ClientInvalidTargetException(player)
        else:
            for stack in range(stacks):
                self.tell(player, 'Giving you %i (stack #%i) of %i' % (self._stack_size, stack, item))
                self.send_command('give %s %i %i' % (player, item, self._stack_size))
            if remainder is not 0:
                self.tell(player, 'Giving you the remaining %i of %i' % (remainder, item))
                self.send_command('give %s %i %i' % (player, item, remainder))

    def tell(self, target, message, no_wrap=False):
        if player.lower() not in self.players:
            raise ClientInvalidTargetException(player)
        else:
            if no_wrap:
                self.send_command('tell %s %s' % (target, message))
            else:
                message = wrap(
                    message,
                    width=self._line_width,
                    subsequent_indent=self._tell_wrap_indent)
                for line in message:
                    self.send_command('tell %s %s' % (target, line))
                
    def tp(self, source, destination):
        if source.lower() not in self.players:
            raise ClientInvalidTargetException(source)
        elif destination.lower() not in self.players:
            raise ClientInvalidTargetException(destination)
        else:
            self.send_command('tp %s %s' % (source, destination))