import json
import os
from collections import Counter

def save_results(all_data, txt_path, json_path):
    if os.path.dirname(txt_path):
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
    
    with open(json_path, 'w') as f:
        json.dump(all_data, f, indent=4)
    
    with open(txt_path, 'w') as f:
        for target, hops in all_data.items():
            f.write(f"Traceroute Report for: {target}\n")
            f.write("=" * 85 + "\n")
            header = f"{'Hop':<4} {'Reply IP':<18} {'Domain Name':<30} {'ICMP':<10} {'UDP':<10} {'TCP':<10}\n"
            f.write(header)
            f.write("-" * 85 + "\n")
            
            for hop in hops:
                ttl = hop['ttl']
                rtts = []
                reply_ip = "*"
                reply_name = "*"

                for p in hop["probes"]:
                    rtt_val = f"{p['rtt_ms']:.2f}ms" if p['rtt_ms'] else "*"
                    rtts.append(rtt_val)
                    
                    if p['reply_ip'] and reply_ip == "*":
                        reply_ip = p['reply_ip']
                        reply_name = p['reply_name'] if p['reply_name'] else "*"

                row = f"{ttl:<4} {reply_ip:<18} {str(reply_name)[:28]:<30} {rtts[0]:<10} {rtts[1]:<10} {rtts[2]:<10}\n"
                f.write(row)
            
            f.write("\n" + "=" * 30 + " STATISTICAL SUMMARY " + "=" * 30 + "\n")
            f.write(f"{'Hop':<5} {'Main IP':<20} {'Avg RTT':<15} {'Packet Loss':<12}\n")
            f.write("-" * 85 + "\n")
            
            for hop in hops:
                ttl = hop['ttl']
                probes = hop['probes']
                
                lost = sum(1 for p in probes if p["status"] == "TIMEOUT")
                loss_pct = (lost / len(probes)) * 100
                
                valid_rtts = [p["rtt_ms"] for p in probes if p["rtt_ms"] is not None]
                avg_rtt = f"{sum(valid_rtts)/len(valid_rtts):.2f} ms" if valid_rtts else "N/A"
                
                ips = [p["reply_ip"] for p in probes if p["reply_ip"]]
                main_ip = Counter(ips).most_common(1)[0][0] if ips else "*"
                
                summary_line = f"{ttl:<5} {main_ip:<20} {avg_rtt:<15} {loss_pct:>5.1f}%\n"
                f.write(summary_line)
                
            f.write("=" * 85 + "\n\n")

    print(f"Results successfully saved to {txt_path} and {json_path}")