#!/usr/bin/env python

import ConfigParser
from time import time
from subprocess import Popen, PIPE
import socket
import select
import sys
import os.path
from StringIO import StringIO
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class ServerException(Exception):
    pass

class Server(object):
    default_config = """
    [%s]
    port=9001
    socket_type=AF_UNIX
    listen_addr=%s.sock
    listen_timeout=10
    socket_buffer_size=1024
    [java]
    server_jar=minecraft_server.jar
    server_gui=false
    heap_max=1024M
    heap_min=1024M
    extra_options=
    """
    _config_name = 'Server'

    def __init__(self, config=None):
        self.default_config = self.__class__.default_config % (
            self._config_name, self._config_name)
        if config is None:
            self.load_config(self.default_config)
        else:
            self.load_config(config)
        self.running = False

    def __del__(self):
        if self.running:
            self.stop

    def start(self):
        self.running = True
        try:
            self._start_listening()
            self._start_minecraft()
            self._run()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        for client in self.clients:
            try:
                client.close()
            except socket.error:
                pass
        self.socket.close()
        if self.config[self._config_name]['socket_type'] == 'AF_UNIX':
            os.remove(self.config[self._config_name]['listen_addr'])
        self.send_minecraft_command('stop')
        self.minecraft_server.wait()
        self.running = False

    def dispatch_event(self, client, line):
        if line.startswith('|'):
            self.send_minecraft_command(line.lstrip('|'))
        elif line.startswith('!'):
            try:
                self.public[line.lstrip('!').split()[0]] = pickle.loads(' '.join(line.lstrip('?').split()[1:]))
            except pickle.PickleError:
                self.send_peer(client, '+503')
            else:
                self.send_peer(client, '+200')
        elif line.startswith('?'):
            try:
                self.send_peer(client, '!%s %s' % (line.lstrip('?').split()[0], pickle.dumps(self.public[line.lstrip('?').split()[0]])))
            except IndexError:
                #no token, send 503 error
                self.send_peer(client, '+503')
            except KeyError:
                #var not found, send 404
                self.send_peer(client, '+404')
        elif line.startswith('+'):
            if self.authenticate_client(client, line[1:]):
                self.send_peer(client, '+200')
            else:
                self.send_peer(client, '+403')
                self.remove_peer(client)
        elif line.startswith('-'):
            self.send_peer(client, '-200')
            self.remove_peer(client)
        else: pass
        
    def authenticate_client(client, initial_message):
        return True

    def _run(self):
        self.clients = {}
        self.public = {}

        while self.running:
            try:
                read_ready, write_ready, except_ready = select.select(
                    self.outputs,
                    self.inputs,
                    [],
                    1.0)
            except Exception:
                continue

            for sock in read_ready:
                if sock is sys.stdin:
                    self.send_minecraft_command(sock.readline())
                elif sock is self.socket:
                    client, address = self.socket.accept()
                    self.outputs.append(client)
                    self.clients[client] = {
                        'socket': client,
                        'connected': time(),
                    }
                    self.send_peer(client, '+')
                elif sock in self.clients:
                    try:
                        buffer = sock.recv(self.config[self._config_name]['socket_buffer_size'])
                        if not buffer:
                            self.remove_peer(sock)
                        else:
                            self.dispatch_event(sock, buffer.strip())
                    except Exception:
                        self.remove_peer(sock)
                elif sock is self.minecraft_server.stderr or \
                    sock is self.minecraft_server.stdout:
                    line = sock.readline().rstrip()
                    if not line:
                        self.stop()
                    else:
                        for client in self.clients:
                            if self.send_peer(client, line) is 0:
                                self.remove_peer(sock)

    def send_peer(self, peer, message):
        try:
            return peer.send(message + '\r\n')
        except Exception:
            pass

    def remove_peer(self, peer):
        try:
            del self.clients[peer]
        except KeyError:
            pass
        try:
            self.outputs.remove(peer)
        except ValueError:
            pass

        peer.close()

    def _start_minecraft(self):
        command = [
            'java',
            self.config['java']['extra_options'],
            '-Xmx%s' % self.config['java']['heap_max'],
            '-Xms%s' % self.config['java']['heap_min'],
            '-jar',
            self.config['java']['server_jar'],
            self.config['java']['server_gui'],
        ]
        self.minecraft_server = Popen(
            command,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE)
        self.outputs = [
            self.socket,
            self.minecraft_server.stderr,
            self.minecraft_server.stdout,
            sys.stdin,
        ]
        self.inputs = []
        self.start_time = time()

    def _start_listening(self):
        try:
            socket_type = getattr(socket,
                self.config[self._config_name]['socket_type'])
        except AttributeError:
            socket_type = socket.AF_INET
        self.socket = socket.socket(socket_type, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if socket_type == socket.AF_UNIX:
            self.socket.bind(self.config[self._config_name]['listen_addr'])
        else:
            self.socket.bind(self.config[self._config_name]['listen_addr'],
                self.config[self._config_name]['listen_port'])
        self.socket.listen(self.config[self._config_name]['listen_timeout'])
        
    def send_minecraft_command(self, command):
        self.minecraft_server.stdin.write(command + '\n')

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
            raise ServerException('Couldn\'t find parser for config')

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
