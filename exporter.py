"""Preserve every probe in JSON and summarize all repetitions in text."""

import json
from collections import Counter
from pathlib import Path


def _mean_rtt(probes):
    values = [p["rtt_ms"] for p in probes if p.get("rtt_ms") is not None]
    return f"{sum(values) / len(values):.2f}ms" if values else "*"


def save_results(all_data, txt_path, json_path):
    for path in (txt_path, json_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(all_data, file, indent=4, allow_nan=False)
    with open(txt_path, "w", encoding="utf-8") as file:
        for target, hops in all_data.items():
            file.write(f"Traceroute Report for: {target}\n")
            file.write("=" * 106 + "\n")
            file.write("RTTs are means of all available replies for each protocol at this TTL.\n")
            file.write(f"{'Hop':<5} {'Reply IP':<18} {'Domain Name':<30} {'ICMP mean':<14} {'UDP mean':<14} {'TCP mean':<14}\n")
            for hop in hops:
                probes = hop.get("probes", [])
                first_reply = next((p for p in probes if p.get("reply_ip")), {})
                rtts = [_mean_rtt([p for p in probes if p.get("protocol") == protocol])
                        for protocol in ("ICMP", "UDP", "TCP")]
                file.write(f"{hop['ttl']:<5} {first_reply.get('reply_ip', '*'):<18} "
                           f"{str(first_reply.get('reply_name') or '*')[:28]:<30} "
                           f"{rtts[0]:<14} {rtts[1]:<14} {rtts[2]:<14}\n")
            file.write("\nSTATISTICAL SUMMARY (all protocols combined)\n")
            file.write(f"{'Hop':<5} {'Main IP':<20} {'Mean RTT':<15} {'Attempts':<10} {'Timeout %':<12} {'Errors':<8}\n")
            for hop in hops:
                probes = hop.get("probes", [])
                lost = sum(p.get("status") == "TIMEOUT" for p in probes)
                errors = sum(p.get("status") == "ERROR" for p in probes)
                loss = f"{lost / len(probes) * 100:.1f}%" if probes else "N/A"
                ips = [p["reply_ip"] for p in probes if p.get("reply_ip")]
                main_ip = Counter(ips).most_common(1)[0][0] if ips else "*"
                file.write(f"{hop['ttl']:<5} {main_ip:<20} {_mean_rtt(probes):<15} "
                           f"{len(probes):<10} {loss:<12} {errors:<8}\n")
            file.write("Timeout % measures missing probe responses, not end-to-end traffic loss.\n\n")
    print(f"Results successfully saved to {txt_path} and {json_path}")
