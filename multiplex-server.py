#!/usr/bin/env python

import ConfigParser
from time import time
from subprocess import Popen, PIPE
import socket
import select
import sys

class MultiplexServerException(Exception):
    pass

class MultiplexServer(object):
    default_config = """
    """

    def __init__(self, config=None):
        if config is None:
            self.load_config(self.__class__.default_config)
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
            self.send_minecraft_command('stop')
            self.minecraft_server.wait()

    def stop(self):
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.socket.close()
        if self.config['socket_type'] == 'AF_UNIX':
            import os
            os.remove(self.config['listen_addr'])
        self.running = False

    def _run(self):
        self.clients = {}
        keep_running = True

        while keep_running:
            try:
                read_ready, write_ready, except_ready = select.select(
                    self.outputs,
                    self.inputs,
                    [],
                    1.0)
            except Exception:
                continue

            if not read_ready:
                for client in self.clients:
                    if time() - self.clients[client]['connected'] > \
                        self.config['password_gracetime'] and \
                        not self.require_password:
                        self.remove_peer(client)
                        break
            else:
                for sock in read_ready:
                    if sock is sys.stdin:
                        self.send_minecraft_command(sock.readline())
                    elif sock is self.socket:
                        client, address = self.socket.accept()
                        self.outputs.append(client)

                        if self.config['password']:
                            self.send_peer(client, '- Enter password')
                        else:
                            self.send_pear(client, '+ Welcome')

                        self.clients[client] = {
                            'socket': client,
                            'auth': bool(self.config['password']),
                            'connected': time(),
                        }
                    elif sock in self.clients:
                        try:
                            buffer = sock.recv(256)
                            if not buffer:
                                self.remove_peer(sock)
                            else:
                                if not self.clients[sock]['auth']:
                                    if buffer.rstrip() != self.config['password']:
                                        self.send_peer(
                                            sock,
                                            '- Bad password')
                                        self.remove_peer(sock)
                                    else:
                                        self.clients[sock]['auth'] = True
                                        self.send_pear(sock, '+ Password accepted')
                                    continue

                                if buffer.rstrip() == '.close':
                                    self.send_peer(sock, '+ Closing')
                                    self.remove_peer(sock)
                                elif buffer.rstrip() == '.time':
                                    self.send_peer(sock, '+ Start time %i' % int(self.start_time))
                                else:
                                    self.send_minecraft_command(buffer.rstrip())
                        except Exception:
                            self.remove_peer(sock)
                    elif sock is self.minecraft_server.stderr or \
                        sock is self.minecraft_server.stdout:
                        line = sock.readline().rstrip()
                        if not line:
                            keep_running = False
                        else:
                            for client in self.clients:
                                if clients[client]['auth']:
                                    if self.send_peer(client, line) is 0:
                                        self.remove_peer(client)

    def send_peer(self, peer, message):
        try:
            return peer.send('%s\r\n' % message)
        except Exception:
            pass

    def remove_peer(self, peer):
        try:
            self.clients.pop(peer)
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
            '-Xmx%s' % self.config['java_heap_max'],
            '-Xms%s' % self.config['java_heap_min'],
            '-jar',
            self.config['server_jar'],
            self.config['server_gui'],
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
        listen_timeout = 10
        try:
            socket_type = getattr(socket, self.config['socket_type'])
        except AttributeError:
            socket_type = socket.AF_INET
        self.socket = socket.socket(socket_type, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if socket_type == socket.AF_UNIX:
            self.socket.bind(self.config['listen_addr'])
        else:
            self.socket.bind(self.config['listen_addr'], self.config['listen_port'])
        self.socket.listen(listen_timeout)
        
    def send_minecraft_command(self, command):
        self.minecraft_server.stdin.write('%s\n' % command)

    def load_config(self, config):
        pass

    def save_config(self):
        pass

if __name__ == '__main__':
    server = MultiplexServer(sys.argv[1])
    server.start()