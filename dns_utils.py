import socket


def resolve_ip(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except OSError:
        return None
