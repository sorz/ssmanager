import json
import logging
from os import makedirs, path
from subprocess import Popen
from socket import socket, AF_UNIX, SOCK_DGRAM


class Server():
    def __init__(self, port, password, method, host='0.0.0.0', timeout=10,
                 udp=True, ota=False, fast_open=True):
        self.port = port
        self._udp = udp
        self._config = dict(server_port=port, password=password, method=method,
                            server=host, auth=ota, timeout=timeout,
                            fast_open=fast_open)

    def start(self, manager_addr, temp_dir, ss_bin='/usr/bin/ss-server'):
        config_path = path.join(temp_dir, 'ss-%s.json' % self.port)
        with open(config_path, 'w') as f:
            json.dump(self._config, f)

        args = [ss_bin, '-c', config_path, '--manager-address', manager_addr]
        if self._udp:
            args.append('-u')

        self._proc = Popen(args)

    def shutdown(self):
        """Shutdown this server."""
        self._proc.terminate()


class Manager():
    def __init__(self, manager_addr='/tmp/manager.sock', temp_dir='/tmp/shadowsocks/'):
        self._manager_addr = manager_addr
        self._temp_dir = temp_dir
        makedirs(temp_dir, exist_ok=True)

        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(manager_addr)

        self._servers = dict()

    def close(self):
        for port, server in self._servers.items():
            server.shutdown()
        self._sock.close()

    def add(self, server):
        if server.port in self._servers:
            if server == self._servers[server.port]:
                logging.debug('Same configuration, ignore.')
                return True
            else:
                logging.debug('Conflicting server found, shutdown it.')
                server.shutdown()
        self._servers[server.port] = server
        server.start(self._manager_addr, self._temp_dir)
        print(self._sock.recvmsg(256))

