import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Multi-Protocol Traceroute Tool")
    
    parser.add_argument("input_file", help="Path to the txt file containing target IPs")
    
    parser.add_argument("-m", "--max_ttl", type=int, default=30, help="Max TTL (default: 30)")
    parser.add_argument("-M", "--min_ttl", type=int, default=1, help="Initial TTL (default: 1)")
    parser.add_argument("-p", "--port", type=int, default=80, help="Destination port for UDP/TCP (default: 80)")
    parser.add_argument("-q", "--queries", type=int, default=3, help="Number of series per hop (default: 3)")
    parser.add_argument("-t", "--timeout", type=int, default=2, help="Waiting time for response (default: 2s)")
    parser.add_argument("-s", "--size", type=int, default=56, help="Packet size (default: 56 bytes)")
    parser.add_argument("-w", "--wait", type=float, default=0.1, help="Inter-packet delay (default: 0.1s)")
    
    parser.add_argument("-n", "--no-dns", action="store_true", help="Do not resolve IP addresses to names")
    return parser.parse_args()