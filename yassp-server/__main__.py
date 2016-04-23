#!/usr/bin/env python3
from argparse import ArgumentParser

from .manager import Manager, Server


def get_args():
    parser = ArgumentParser(description='YASSP-Server')
    parser.add_argument('address', metavar='SS-MANAGER-UNIX-ADDRESS')

    return parser.parse_args()


def main():
    args = get_args()
    manager = Manager()
    manager.start()
    server = Server(5123, 'test', 'chacha20')
    try:
        manager.add(server)
        manager._stat_thread.join()
    finally:
        manager.stop()


if __name__ == '__main__':
    main()

