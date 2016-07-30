import os
import time
import json
import logging
from subprocess import Popen, DEVNULL
from threading import Thread
from socket import socket, AF_UNIX, SOCK_DGRAM

from . import Server, _Manager


TIMEOUT = 90  # Must > 30
CHECK_PERIOD = 180


class Manager(_Manager):

    def __init__(self, print_ss_log=True, manager_addr='/tmp/manager.sock',
                 temp_dir='/tmp/shadowsocks/', ss_bin='/usr/bin/ss-server'):
        super().__init__()
        self._sock = None
        self._print_ss_log = print_ss_log
        self._ss_bin = ss_bin
        self._manager_addr = manager_addr
        self._temp_dir = temp_dir

        self._stat_thread = Thread(target=self._receiving_stat, daemon=True)
        self._restart_thread = Thread(target=self._restarting_inactive_servers, daemon=True)

    def start(self):
        super().start()
        os.makedirs(self._temp_dir, exist_ok=True)
        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(self._manager_addr)

        self._stat_thread.start()
        self._restart_thread.start()
        logging.info('Manager started.')

    def stop(self):
        super().stop()
        if self._sock is not None:
            self._sock.close()
        if os.path.exists(self._manager_addr):
            os.remove(self._manager_addr)

    def _start_instance(self, server):
        """Start `ss-server` process."""
        config_path = os.path.join(self._temp_dir, 'ss-%s.json' % server.port)
        with open(config_path, 'w') as f:
            json.dump(server._config, f)

        args = [self._ss_bin, '-c', config_path,
                '--manager-address', self._manager_addr]
        if server._udp:
            args.append('-u')

        if self._print_ss_log:
            output = None  # inherited from self
        else:
            output = DEVNULL
        server._proc = Popen(args, stdout=output, stderr=output)
        server.is_running = True
        logging.debug('ss-server at %s:%d started.' % (server.host, server.port))

    def _stop_instance(self, server):
        """Stop `ss-server` process."""
        server.is_running = False
        server._proc.terminate()
        logging.debug('ss-server at %s:%d stopped.' % (server.host, server.port))

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

    def _restarting_inactive_servers(self):
        while self._is_running:
            inactives = []
            for port, server in self._servers.items():
                if server.is_running:
                    if time.time() - server.last_active_time > TIMEOUT:
                        inactives.append(server)
                        logging.warning('Server (:%s) is inactive, restarting it...' % port)
            for server in inactives:
                self.remove(server)
                self.add(server)
            time.sleep(CHECK_PERIOD)


class ServerAlreadyExistError(Exception):
    pass

