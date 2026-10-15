# Multi-Protocol Traceroute & Topology Explorer

## Project Structure
- `main.py`: The main entry point. Orchestrates target loading, tracing, and result exporting.
- `tracer.py`: Contains the high-level tracing logic, handling TTL increments and destination reached detection.
- `probes.py`: Low-level network module. Uses Scapy to craft and send ICMP, UDP, and TCP packets.
- `parser.py`: Handles command-line arguments (TTL, timeout, port, etc.).
- `dns_utils.py`: Utility module for reverse DNS lookups.
- `exporter.py`: Formats and saves the results into a standardized report and JSON for visualization.

## Design Choices
- Multi-Protocol Concurrency: Unlike standard traceroute, we probe ICMP, UDP, and TCP simultaneously to bypass firewalls and observe path variations.
- Statistical Aggregation: Includes automated packet loss and average RTT calculations per hop.
- Fault Tolerance: Gracefully handles network timeouts and user interrupts (Ctrl+C) while preserving data.

## Features
- Input from a `.txt` file containing multiple targets
- Adjustable TTL range, timeout, packet size, port, and query count
- Per-hop multi-protocol probing
- Human-readable text report
- Interactive topology explorer with filtering and detail inspection

## Usage
See `HOWTO.md` for installation, execution, and frontend instructions.