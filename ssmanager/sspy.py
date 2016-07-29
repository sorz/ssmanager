import os
import time
import json
import logging
from subprocess import Popen, DEVNULL
from threading import Thread
from socket import socket, AF_UNIX, SOCK_DGRAM

from . import _Server, _Manager


TIMEOUT = 90  # Must > 30
CHECK_PERIOD = 180


class Server(_Server):

    def start(self, sock):
        self.is_running = True
        self.last_active_time = time.time()
        sock.send(b'add: ' + json.dumps(self._config).encode())
        if sock.recv(1506) != b'ok':
            raise UnexpectedServerResponse()
        logging.debug('ss-server at %s:%d started.' % (self.host, self.port))

    def shutdown(self, sock):
        self.is_running = False
        sock.send(b'remove: {"server_port":%s}' % str(self.port).encode())
        if sock.recv(1506) != b'ok':
            raise UnexpectedServerResponse()
        logging.debug('ss-server at %s:%d stopped.' % (self.host, self.port))


class Manager(_Manager):

    def __init__(self, print_ss_log=True, manager_addr='/tmp/manager.sock',
                 client_addr='/tmp/manager-client.sock', ss_bin='/usr/bin/ssserver'):
        super().__init__()
        self._sock = None
        self._ss_bin = ss_bin
        self._ss_proc = None
        self._print_ss_log = print_ss_log
        self._manager_addr = manager_addr
        self._client_addr = client_addr

        #self._stat_thread = Thread(target=self._receiving_stat, daemon=True)
        #self._restart_thread = Thread(target=self._restarting_inactive_servers, daemon=True)

    def start(self):
        super().start()
        if self._print_ss_log:
            output = None  # inherited from self
        else:
            output = DEVNULL
        args = [self._ss_bin, '--manager-address', self._manager_addr]
        self._ss_proc = Popen(args, stdout=output, stderr=output)
        time.sleep(0.5)  # Waiting for ssserver started.
        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(self._client_addr)
        self._sock.connect(self._manager_addr)
        self._sock.send(b'remove: {"server_port": 8388}')
        if self._sock.recv(1506) != b'ok':
            raise UnexpectedServerResponse()

        #self._stat_thread.start()
        #self._restart_thread.start()
        logging.info('Manager started.')

    def stop(self):
        super().stop()
        if self._sock is not None:
            self._sock.close()
        if self._ss_proc is not None:
            self._ss_proc.terminate()
        if os.path.exists(self._manager_addr):
            os.remove(self._manager_addr)
        if os.path.exists(self._client_addr):
            os.remove(self._client_addr)

    def _start_instance(self, server):
        server.start(self._sock)

    def _stop_instance(self, server):
        server.shutdown(self._sock)

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

class UnexpectedServerResponse(Exception):
    pass
