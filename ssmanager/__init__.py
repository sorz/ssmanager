import logging
import time


__version__ = '0.2.7'

class Server():
    """Store configuration about one server instance."""

    def __init__(self, port, password, method, host='0.0.0.0', timeout=180,
                 udp=True, fast_open=True, **extra_config):
        self._traffic = 0
        self._is_running = False
        self.port = port
        self.host = host
        self._udp = udp
        self._config = dict(server_port=port, password=password, method=method,
                            server=host, timeout=timeout, fast_open=fast_open)
        self._config.update(extra_config)

    def __eq__(self, other):
        if not isinstance(other, Server):
            return False
        return self.port == other.port and self._udp == other._udp \
               and self._config == other._config

    @property
    def is_running(self):
        return self._is_running

    @is_running.setter
    def is_running(self, state):
        self._is_running = state
        self.last_active_time = time.time()

    @property
    def traffic(self):
        return self._traffic

    @traffic.setter
    def traffic(self, traffic):
        self._traffic = traffic
        self.last_active_time = time.time()


class _Manager():

    def __init__(self):
        self._servers = dict()
        self._is_running = False

    def _start_instance(self, server):
        raise NotImplementedError()

    def _stop_instance(self, server):
        raise NotImplementedError()

    def start(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def add(self, server):
        """Add & start a ss-server."""
        if server.port in self._servers:
            raise ServerAlreadyExistError
        self._servers[server.port] = server
        self._start_instance(server)

    def update(self, servers):
        """Add & remove a set of servers in batch.

        The server list inside `Manager` will be replaced by `servers`.
        """
        servers = {s.port: s for s in servers}
        old_ports = set(self._servers.keys())
        new_ports = set(servers.keys())

        for port in old_ports - new_ports:
            self.remove(port)

        for port in new_ports - old_ports:
            self.add(servers[port])

        for port in new_ports & old_ports:
            if servers[port] != self._servers[port]:
                self.remove(port)
                self.add(servers[port])

    def remove(self, server):
        """Stop a server and remove from internal list."""
        if isinstance(server, int):
            server = self._servers[server]
        del self._servers[server.port]
        self._stop_instance(server)

    def stat(self):
        """Return a dict of { port_number: total_traffic_in_bytes }."""
        return {p: s.traffic for p, s in self._servers.items()}


class ServerAlreadyExistError(Exception):
    pass

# Compatible with old API
from .sslibev import Manager
