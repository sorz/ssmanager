#!/usr/bin/env python3
import time
import logging

from ssmanager import Manager, Server


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-s: %(message)s')
    manager = Manager(print_ss_log=True)
    try:
        manager.start()
        server = Server(5123, 'test', 'chacha20')
        servers = [server, Server(5124, 'test', 'chacha20'),
                   Server(5123, 'test', 'chacha20')]
        manager.add(server)
        time.sleep(5)
        manager.update(servers)
        manager._stat_thread.join()
    except KeyboardInterrupt:
        logging.info('Stopped by ^C.')
    finally:
        manager.stop()


if __name__ == '__main__':
    main()

