import time
import json
import logging
from os import makedirs, path
from subprocess import Popen
from threading import Thread
from socket import socket, AF_UNIX, SOCK_DGRAM


TIMEOUT = 60  # Must > 30
CHECK_PERIOD = 180

class Server():
    traffic = 0
    is_running = False

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
        self.is_running = True
        self.last_active_time = time.time()

    def shutdown(self):
        """Shutdown this server."""
        self.is_running = False
        self._proc.terminate()


class Manager():
    def __init__(self, manager_addr='/tmp/manager.sock', temp_dir='/tmp/shadowsocks/'):
        self._manager_addr = manager_addr
        self._temp_dir = temp_dir
        makedirs(temp_dir, exist_ok=True)

        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(manager_addr)
        self._stat_thread = Thread(target=self._receiving_stat, daemon=True)
        self._restart_thread = Thread(target=self._restarting_inactive_servers, daemon=True)

        self._servers = dict()

    def start(self):
        self._is_running = True
        self._stat_thread.start()
        self._restart_thread.start()

    def stop(self):
        self._is_running = False
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

    def remove(self, server):
        if isinstance(server, int):
            server = self._servers[server]
        del self._servers[server.port]
        server.shutdown()

    def stat(self):
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
                        logging.warning('Server (:%s) is inactive, restarting it...')
                        server.shutdown()
                        server.start(self._manager_addr, self._temp_dir)
            time.sleep(CHECK_PERIOD)

