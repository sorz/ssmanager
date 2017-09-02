import os
import time
import json
import logging
from subprocess import Popen, DEVNULL
from threading import Thread, Event, RLock
from socket import socket, AF_UNIX, SOCK_DGRAM

from . import Server, _Manager


SOCK_RESPONSE_TIMEOUT = 10
MIN_RESTART_INTERVAL = 30

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
        self._ok = Event()
        self._sock_lock = RLock()
        self._recv_thread = Thread(target=self._receiving, daemon=True)
        self._restart_thread = Thread(target=self._restarting, daemon=True)

    def start(self):
        super().start()
        self._start_process()
        self._restart_thread.start()
        logging.info('Manager started.')

    def stop(self):
        super().stop()
        if self._sock is not None:
            self._sock.close()
        if self._ss_proc is not None:
            self._ss_proc.terminate()
        self._clean_socket()

    def _clean_socket(self):
        """Remove UNIX domain socket files if exists."""
        if os.path.exists(self._manager_addr):
            os.remove(self._manager_addr)
        if os.path.exists(self._client_addr):
            os.remove(self._client_addr)

    def _send(self, message: str):
        """Send a message to SS process and waiting for "ok"."""
        with self._sock_lock:
            self._sock.send(message.encode())
            if not self._ok.wait(SOCK_RESPONSE_TIMEOUT):
                raise SSServerConnectionTimeout()

    def _start_process(self):
        if self._print_ss_log:
            output = None  # inherited from self
        else:
            output = DEVNULL
        args = [self._ss_bin, '--manager-address', self._manager_addr,
                '-s', '127.0.1.2', '-p', '0']
        self._ss_proc = Popen(args, stdout=output, stderr=output)
        self._sock = socket(AF_UNIX, SOCK_DGRAM)
        self._sock.bind(self._client_addr)
        # Waiting for ssserver started.
        connected = False
        for t in 0.01, 0.1, 0.2, 0.4, 0.8, 1, 2, 4:
            time.sleep(t)
            try:
                self._sock.connect(self._manager_addr)
            except (FileNotFoundError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
        if not connected:
            logging.critical('Cannot connect to ssserver process on %s.',
                             self._manager_addr)
            raise SSServerConnectionError()

        if not self._recv_thread.is_alive():
            self._recv_thread = Thread(target=self._receiving, daemon=True)
            self._recv_thread.start()
        self._send('remove: {"server": "127.0.1.2"}')
        logging.info('Shadowsocks process started.')

    def _start_instance(self, server):
        server.is_running = True
        config = server._config.copy()
        self._send('add: ' + json.dumps(config))
        logging.debug('ss-server at %s:%d started.' % (server.host, server.port))

    def _stop_instance(self, server):
        server.is_running = False
        self._send('remove: {"server_port": %d}' % server.port)
        logging.debug('ss-server at %s:%d stopped.' % (server.host, server.port))


    def _restarting(self):
        """A thread to watch SS process and try restart it when
        process exited.
        """
        last_restart = time.time()
        while self._is_running:
            returncode = self._ss_proc.wait()
            logging.warning('Shadowsocks process exited with code %s.', returncode)
            with self._sock_lock:  # To block sock operations until process restarted.
                restart_gap = time.time() - last_restart
                if restart_gap < MIN_RESTART_INTERVAL:
                    sleep = MIN_RESTART_INTERVAL - restart_gap
                    logging.info('Waiting %d seconds before restart.', sleep)
                    time.sleep(sleep)
                logging.info('Restarting Shadowsocks process.')
                last_restart = time.time()
                self._clean_socket()
                self._start_process()
                for server in self._servers.values():
                    self._start_instance(server)

    def _receiving(self):
        while self._is_running:
            data, _ = self._sock.recvfrom(2048)
            if data == b'ok':
                self._ok.set()
                continue

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
                self._servers[port].traffic += traffic

class ServerAlreadyExistError(Exception):
    pass

class SSServerConnectionError(ConnectionError):
    pass

class SSServerConnectionTimeout(SSServerConnectionError):
    pass
