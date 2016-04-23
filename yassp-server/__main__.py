#!/usr/bin/env python3
from argparse import ArgumentParser

from .manager import Manager


def get_args():
    parser = ArgumentParser(description='YASSP-Server')
    parser.add_argument('address', metavar='SS-MANAGER-UNIX-ADDRESS')

    return parser.parse_args()


def main():
    args = get_args()
    manager = Manager(args.address)
    print(manager.add(5123, 'test', 'chacha20'))
    manager.close()


if __name__ == '__main__':
    main()

