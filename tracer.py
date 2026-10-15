import time
import sys
from probes import send_icmp_probe, send_udp_probe, send_tcp_probe

def run_trace(target_ip, args):
    path_results = []
    consecutive_timeouts = 0  
    
    try:
        for ttl in range(args.min_ttl, args.max_ttl + 1):
            hop_data = {"ttl": ttl, "probes": []}
            reached_destination = False
            responded_in_this_hop = False 
            
            for _ in range(args.queries):
                for probe_func, name in [
                    (send_icmp_probe, "ICMP"),
                    (send_udp_probe, "UDP"),
                    (send_tcp_probe, "TCP")
                ]:
                    try:
                        if name == "ICMP":
                            res = probe_func(target_ip, ttl, args.timeout, args.size)
                        else:
                            res = probe_func(target_ip, ttl, args.port, args.timeout, args.size)
                        
                        hop_data["probes"].append(res)
                        
                        if res["status"] != "TIMEOUT":
                            responded_in_this_hop = True
                        if res["status"] == "REACHED":
                            reached_destination = True
                            
                        time.sleep(args.wait)
                    except Exception as e:
                        print(f"\n[Error in {name} probe]: {e}")

            path_results.append(hop_data)
            print_hop_summary(hop_data)
            
            if not responded_in_this_hop:
                consecutive_timeouts += 1
            else:
                consecutive_timeouts = 0 
            
            if reached_destination:
                print(f"Destination {target_ip} reached at hop {ttl}.")
                break
            
            if consecutive_timeouts >= 3:
                print(f"Skipping {target_ip} due to 3 consecutive timeouts.")
                break
                
    except KeyboardInterrupt:
        print("\n[User Interrupted] Saving current results and exiting")
        return path_results
            
    return path_results

def print_hop_summary(hop_data):
    ttl = hop_data["ttl"]
    display_ip = "*"
    for p in hop_data["probes"]:
        if p["reply_ip"]:
            display_ip = p["reply_ip"]
            break
    print(f"{ttl}\t{display_ip}")