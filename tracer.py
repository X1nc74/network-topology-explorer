import socket
import time
from probes import send_icmp_probe, send_tcp_probe, send_udp_probe


class TraceInterrupted(Exception):
    """Carry completed observations to the CLI when the user interrupts."""

    def __init__(self, results):
        super().__init__("Trace interrupted")
        self.results = results


def run_trace(target_ip, args):
    path_results = []
    hop_data = None
    consecutive_timeouts = 0
    try:
        destination = socket.gethostbyname(target_ip)
        for ttl in range(args.min_ttl, args.max_ttl + 1):
            hop_data = {"ttl": ttl, "probes": []}
            for _ in range(args.queries):
                for probe_func, protocol in [
                    (send_icmp_probe, "ICMP"),
                    (send_udp_probe, "UDP"),
                    (send_tcp_probe, "TCP"),
                ]:
                    try:
                        extra = {"packet_size": args.size, "resolve_dns": not args.no_dns}
                        if protocol == "ICMP":
                            result = probe_func(destination, ttl, args.timeout, **extra)
                        else:
                            result = probe_func(destination, ttl, args.port, args.timeout, **extra)
                    except Exception as exc:
                        result = {
                            "protocol": protocol, "target_ip": destination, "ttl": ttl,
                            "reply_ip": None, "reply_name": None, "rtt_ms": None,
                            "status": "ERROR", "error": str(exc),
                        }
                        print(f"\n[Error in {protocol} probe]: {exc}")
                    hop_data["probes"].append(result)
                    time.sleep(args.wait)

            path_results.append(hop_data)
            print_hop_summary(hop_data)
            responded = any(p.get("reply_ip") for p in hop_data["probes"])
            consecutive_timeouts = 0 if responded else consecutive_timeouts + 1
            if any(p["status"] == "REACHED" for p in hop_data["probes"]):
                print(f"Destination {target_ip} reached at hop {ttl}.")
                break
            if consecutive_timeouts >= 3:
                print(f"Stopping {target_ip} after 3 consecutive hops without replies.")
                break
    except KeyboardInterrupt as exc:
        if hop_data and hop_data["probes"] and (not path_results or path_results[-1] is not hop_data):
            path_results.append(hop_data)
        raise TraceInterrupted(path_results) from exc
    return path_results


def print_hop_summary(hop_data):
    display_ip = next((p["reply_ip"] for p in hop_data["probes"] if p.get("reply_ip")), "*")
    print(f"{hop_data['ttl']}\t{display_ip}")
