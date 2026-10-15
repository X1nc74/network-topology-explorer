from scapy.all import IP, ICMP, UDP, TCP, sr1
from dns_utils import resolve_ip
import time


def send_icmp_probe(target_ip, ttl, timeout, packet_size=56):
    #Send one ICMP probe with the given TTL and return a normalized result dict.
    packet = IP(dst=target_ip, ttl=ttl) / ICMP() / (b"X" * packet_size)

    start = time.time()
    ans = sr1(packet, timeout=timeout, verbose=0)
    end = time.time()

    if ans is None:
        return {
            "protocol": "ICMP",
            "target_ip": target_ip,
            "ttl": ttl,
            "reply_ip": None,
            "reply_name": None,
            "rtt_ms": None,
            "status": "TIMEOUT"
        }

    rtt_ms = (end - start) * 1000
    status = "UNKNOWN"

    reply_ip = ans.src
    reply_name = resolve_ip(reply_ip)

    if ans.haslayer(ICMP):
        icmp_layer = ans.getlayer(ICMP)
        if icmp_layer.type == 11:
            status = "TIME_EXCEEDED"
        elif icmp_layer.type == 0:
            status = "REACHED"

    return {
        "protocol": "ICMP",
        "target_ip": target_ip,
        "ttl": ttl,
        "reply_ip": reply_ip,
        "reply_name": reply_name,
        "rtt_ms": round(rtt_ms, 2),
        "status": status
    }


def send_udp_probe(target_ip, ttl, port, timeout, packet_size=56):
    packet = IP(dst=target_ip, ttl=ttl) / UDP(dport=port) / (b"X" * packet_size)

    start = time.time()
    ans = sr1(packet, timeout=timeout, verbose=0)
    end = time.time()

    if ans is None:
        return {
            "protocol": "UDP",
            "target_ip": target_ip,
            "ttl": ttl,
            "reply_ip": None,
            "reply_name": None,
            "rtt_ms": None,
            "status": "TIMEOUT"
        }

    rtt_ms = (end - start) * 1000
    status = "UNKNOWN"

    reply_ip = ans.src
    reply_name = resolve_ip(reply_ip)

    if ans.haslayer(ICMP):
        icmp_layer = ans.getlayer(ICMP)
        if icmp_layer.type == 11:
            status = "TIME_EXCEEDED"
        elif icmp_layer.type == 3 and icmp_layer.code == 3:
            status = "REACHED"

    return {
        "protocol": "UDP",
        "target_ip": target_ip,
        "ttl": ttl,
        "reply_ip": reply_ip,
        "reply_name": reply_name,
        "rtt_ms": round(rtt_ms, 2),
        "status": status
    }
def send_tcp_probe(target_ip, ttl, port, timeout, packet_size=56):
    packet = IP(dst=target_ip, ttl=ttl) / TCP(dport=port, flags="S") / (b"X" * packet_size)

    start = time.time()
    ans = sr1(packet, timeout=timeout, verbose=0)
    end = time.time()

    if ans is None:
        return {
            "protocol": "TCP",
            "target_ip": target_ip,
            "ttl": ttl,
            "reply_ip": None,
            "reply_name": None,
            "rtt_ms": None,
            "status": "TIMEOUT"
        }

    rtt_ms = (end - start) * 1000
    status = "UNKNOWN"

    reply_ip = ans.src
    reply_name = resolve_ip(reply_ip)

    if ans.haslayer(ICMP):
        icmp_layer = ans.getlayer(ICMP)
        if icmp_layer.type == 11:
            status = "TIME_EXCEEDED"

    elif ans.haslayer(TCP):
        tcp_layer = ans.getlayer(TCP)
        if tcp_layer.flags & 0x12:
            status = "REACHED"
        elif tcp_layer.flags & 0x04:
            status = "REACHED"

    return {
        "protocol": "TCP",
        "target_ip": target_ip,
        "ttl": ttl,
        "reply_ip": reply_ip,
        "reply_name": reply_name,
        "rtt_ms": round(rtt_ms, 2),
        "status": status
    }


if __name__ == "__main__":
    # ===== ICMP TEST =====
    # print(send_icmp_probe("8.8.8.8", ttl=1, timeout=2))
    # print(send_icmp_probe("8.8.8.8", ttl=64, timeout=2))
    # print(send_icmp_probe("1.1.1.1", ttl=64, timeout=2))

#    print("=== UDP TEST ===")
#    print(send_udp_probe("8.8.8.8", ttl=1, port=33434, timeout=2))
#    print(send_udp_probe("8.8.8.8", ttl=64, port=33434, timeout=2))

#    print(send_udp_probe("1.1.1.1", ttl=64, port=33434, timeout=2))
#    print(send_udp_probe("8.8.4.4", ttl=64, port=33434, timeout=2))

    # print("=== TCP TEST ===")
    # print(send_tcp_probe("8.8.8.8", ttl=1, port=80, timeout=2))
    # print(send_tcp_probe("8.8.8.8", ttl=64, port=80, timeout=2))
    # print(send_tcp_probe("1.1.1.1", ttl=64, port=80, timeout=2))
    pass