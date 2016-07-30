# ssmanager
A python module interact with manager-mode
[shadowsocks-libev](https://github.com/shadowsocks/shadowsocks-libev)
or [shadowsocks-python](https://github.com/shadowsocks/shadowsocks) server.

> Shadowsocks-libev consists of five components. ss-manager(1) is a controller
> for multi-user management and traffic statistics, using UNIX domain socket
> to talk with `ss-server`.

This module works like `ss-manager`,
except it provide Python API instead of UNIX domain socket or UDP API.

It has own implementation rather than communicate with `ss-manager`, hence
the only dependence is `ss-server`.

Since version 0.2.0, it plays happily with not only ss-libev but also the
Python port.

## Install

```
$ pip install git+https://github.com/sorz/ssmanager.git
```

## Usage

Example:

```
from ssmanager import Server
from ssmanager.sslibev import Manager
# For Python port, use:
# from ssmanager.sspy import Manager

manager = Manager(ss_bin='/usr/bin/ss-server')
# Point to ssserver if using Python port.
manager.start()

server = Server(1234, 'password', 'aes-256-cfb',
                udp=True, ota=True, fast_open=True)
manager.add(server)
manager.remove(server)  # Or manager.remove(1234)

servers = [Server(...), ...]
manager.update(servers)

manager.stat()
# Return a dict of { port_number: total_traffic_in_bytes }.

manager.stop()
```
