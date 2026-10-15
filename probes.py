"""IPv4 probes with a shared result schema and optional reverse DNS."""

import time
from scapy.all import ICMP, IP, TCP, UDP, sr1
from dns_utils import resolve_ip


def _send_probe(protocol, target_ip, ttl, packet, timeout, resolve_dns):
    start = time.perf_counter()
    answer = sr1(packet, timeout=timeout, verbose=0)
    elapsed_ms = (time.perf_counter() - start) * 1000
    result = {
        "protocol": protocol, "target_ip": target_ip, "ttl": ttl,
        "reply_ip": None, "reply_name": None, "rtt_ms": None, "status": "TIMEOUT",
    }
    if answer is None:
        return result

    reply_ip = answer[IP].src
    destination = packet[IP].dst
    status = "UNKNOWN"
    if answer.haslayer(ICMP):
        icmp = answer[ICMP]
        if icmp.type == 11:
            status = "TIME_EXCEEDED"
        elif icmp.type == 3:
            status = "UNREACHABLE"
            if protocol == "UDP" and icmp.code == 3 and reply_ip == destination:
                status = "REACHED"
        elif protocol == "ICMP" and icmp.type == 0 and icmp.code == 0:
            if reply_ip == destination:
                status = "REACHED"
    elif protocol == "TCP" and answer.haslayer(TCP) and reply_ip == destination:
        flags = int(answer[TCP].flags)
        if (flags & 0x12) == 0x12 or flags & 0x04:
            status = "REACHED"

    result.update(
        reply_ip=reply_ip,
        reply_name=resolve_ip(reply_ip) if resolve_dns else None,
        rtt_ms=round(elapsed_ms, 2),
        status=status,
    )
    return result


def send_icmp_probe(target_ip, ttl, timeout, packet_size=56, resolve_dns=True):
    packet = IP(dst=target_ip, ttl=ttl) / ICMP() / (b"X" * packet_size)
    return _send_probe("ICMP", target_ip, ttl, packet, timeout, resolve_dns)


def send_udp_probe(target_ip, ttl, port, timeout, packet_size=56, resolve_dns=True):
    packet = IP(dst=target_ip, ttl=ttl) / UDP(dport=port) / (b"X" * packet_size)
    return _send_probe("UDP", target_ip, ttl, packet, timeout, resolve_dns)


def send_tcp_probe(target_ip, ttl, port, timeout, packet_size=56, resolve_dns=True):
    packet = IP(dst=target_ip, ttl=ttl) / TCP(dport=port, flags="S") / (b"X" * packet_size)
    return _send_probe("TCP", target_ip, ttl, packet, timeout, resolve_dns)
