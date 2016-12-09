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

```python
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

It's easy to build multiple-user/port Shadowsocks servers with a centrally
server who distributes user configurations using ssmanager. A simple example
is following.

Upload a JSON file to, for example, http://example.com/ss-profiles.json.
The JSON contains all profiles of Shadowsocks users:

```javascript
[{port=8001, password='test123', method='chacha20'},
 {port=8002, password='123test', method='aes-256-cfb'}]
```

Following script grab this JSON every 2 minutes and update its configs if
content of the JSON changed. (Exception handling is omited.)

```python
import time, requests
from ssmanager import Server
from ssmanager.sspy import Manager

manager = Manager()

while True:
    profiles = requests.get('http://example.com/ss-profiles.json').json()
    manager.update([Server(**p) for p in profiles])
    time.sleep(120)
```

