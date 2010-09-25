#!/usr/bin/env python

import socket
import select
import re

class MultiplexClientException(Exception):
    pass

class MultiplexClient(object):
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
            self.stop()

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def _run(self):
        pass

    def load_config(self, config):
        pass

    def save_config(self):
        pass

if __name__ == '__main__':
    import sys
    client = MultiplexClient(sys.argv[1])
    client.start()