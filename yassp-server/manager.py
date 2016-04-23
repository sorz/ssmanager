import json
from collections import OrderedDict
from socket import socket, AF_UNIX, SOCK_DGRAM


class Manager():
    def __init__(self, address):
        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind('')
        self._sock.connect(address)

    def close(self):
        self._sock.close()

    def add(self, port, password, method, host='0.0.0.0', timeout=10, ota=False):
        config = OrderedDict(server_port=port, password=password)
        config['method'] = method  # Get around a bug on ss-manager
        config.update(dict(server=host, auth=ota, timeout=timeout))
        self._sock.send(b'add: ' + json.dumps(config).encode())
        return self._sock.recv(256).decode()

