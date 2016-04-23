#!/usr/bin/env python3
from argparse import ArgumentParser


def get_args():
    parser = ArgumentParser(description='YASSP-Server')
    parser.add_argument('address', metavar='SS-MANAGER-UNIX-ADDRESS')

    return parser.parse_args()


def main():
    args = get_args()


if __name__ == '__main__':
    main()

