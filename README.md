# ssmanager
The python module interact with server-mode shadowsocks-libev.

> Shadowsocks-libev consists of five components. ss-manager(1) is a controller
> for multi-user management and traffic statistics, using UNIX domain socket
> to talk with `ss-server`.

This module works like `ss-manager` of
[shadowsocks-libev](https://github.com/shadowsocks/shadowsocks-libev),
except it provide Python API instead of UNIX domain socket or UDP API.

It has own implementation rather than communicate with `ss-manager`, hence
the only dependence is `ss-server`.

