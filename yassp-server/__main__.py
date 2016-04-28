#!/usr/bin/env python3
import time
import logging
from argparse import ArgumentParser

from .manager import Manager, Server


def get_args():
    parser = ArgumentParser(description='YaSSP-Server')
    parser.add_argument('-S', '--ss-server', dest='ss_bin',
                        default='/usr/bin/ss-server',
                        metavar='PATH-TO-SS-SERVER')
    parser.add_argument('-v', '--log-level',
			default=logging.INFO, type=int,
			metavar='LOG-LEVEL',
			help="1 to 50. Default 20, debug 10, verbose 5.")
    return parser.parse_args()


def main():
    args = get_args()
    logging.basicConfig(level=args.log_level,
                        format='%(asctime)s %(levelname)-s: %(message)s')
    manager = Manager()
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

