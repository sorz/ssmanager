import os
import time
import json
import logging
from subprocess import Popen, DEVNULL
from threading import Thread
from socket import socket, AF_UNIX, SOCK_DGRAM


TIMEOUT = 90  # Must > 30
CHECK_PERIOD = 180

class Server():

    def __init__(self, port, password, method, host='0.0.0.0', timeout=10,
                 udp=True, ota=False, fast_open=True):
        self.traffic = 0
        self.is_running = False
        self.port = port
        self.host = host
        self._udp = udp
        self._config = dict(server_port=port, password=password, method=method,
                            server=host, auth=ota, timeout=timeout,
                            fast_open=fast_open)

    def start(self, manager_addr, temp_dir, ss_bin, print_log=None):
        """Start `ss-server` process.

        Not need to call it if you are using `Manager`.
        """
        config_path = os.path.join(temp_dir, 'ss-%s.json' % self.port)
        with open(config_path, 'w') as f:
            json.dump(self._config, f)

        args = [ss_bin, '-c', config_path, '--manager-address', manager_addr]
        if self._udp:
            args.append('-u')

        if print_log:
            output = None  # inherited from self
        else:
            output = DEVNULL
        self._proc = Popen(args, stdout=output, stderr=output)
        self.is_running = True
        self.last_active_time = time.time()
        logging.debug('ss-server at %s:%d started.' % (self.host, self.port))

    def shutdown(self):
        """Stop `ss-server` process.

        Not need to call it if you are using `Manager`.
        """
        self.is_running = False
        self._proc.terminate()
        logging.debug('ss-server at %s:%d stopped.' % (self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, Server):
            return False
        return self.port == other.port and self._udp == other._udp \
               and self._config == other._config


class Manager():

    def __init__(self, print_ss_log=True, manager_addr='/tmp/manager.sock',
                 temp_dir='/tmp/shadowsocks/', ss_bin='/usr/bin/ss-server'):
        self._servers = dict()
        self._sock = None
        self._print_ss_log = print_ss_log
        self._ss_bin = ss_bin
        self._manager_addr = manager_addr
        self._temp_dir = temp_dir

        self._stat_thread = Thread(target=self._receiving_stat, daemon=True)
        self._restart_thread = Thread(target=self._restarting_inactive_servers, daemon=True)

    def start(self):
        os.makedirs(self._temp_dir, exist_ok=True)
        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(self._manager_addr)

        self._is_running = True
        self._stat_thread.start()
        self._restart_thread.start()
        logging.info('Manager started.')

    def stop(self):
        self._is_running = False
        for port, server in self._servers.items():
            server.shutdown()
        if self._sock is not None:
            self._sock.close()
        if os.path.exists(self._manager_addr):
            os.remove(self._manager_addr)

    def add(self, server):
        """Add & start a ss-server.

        `ss-server` process will start before this method return.
        """
        if server.port in self._servers:
            raise ServerAlreadyExistError
        self._servers[server.port] = server
        server.start(self._manager_addr, self._temp_dir, self._ss_bin,
                     self._print_ss_log)

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
        server.shutdown()

    def stat(self):
        """Return a dict of { port_number: total_traffic_in_bytes }."""
        return {p: s.traffic for p, s in self._servers.items()}

    def _receiving_stat(self):
        while self._is_running:
            data, _, _, _ = self._sock.recvmsg(256)
            if data[-1] == 0:  # Remove \x00 tail
                data = data[:-1]
            cmd, data = data.decode().split(':', 1)
            if cmd != 'stat':
                logging.info('Unknown cmd received from ss-server: ' + cmd)
                continue

            stat = json.loads(data.strip())
            for port, traffic in stat.items():
                port = int(port)
                if port not in self._servers:
                    logging.warning('Stat from unknown port (%s) received.' % port)
                    continue
                self._servers[port].traffic = traffic
                self._servers[port].last_active_time = time.time()

    def _restarting_inactive_servers(self):
        while self._is_running:
            for port, server in self._servers.items():
                if server.is_running:
                    if time.time() - server.last_active_time > TIMEOUT:
                        logging.warning('Server (:%s) is inactive, restarting it...' % port)
                        self.remove(server)
                        self.add(server)
            time.sleep(CHECK_PERIOD)


class ServerAlreadyExistError(Exception):
    pass

