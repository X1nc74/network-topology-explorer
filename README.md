# Multi-Protocol Traceroute & Topology Explorer

A Computer Networks midterm project combining a Python/Scapy route-probing CLI with an interactive JavaScript topology explorer. It sends ICMP, UDP and TCP probes with increasing IPv4 TTL values, records responses and round-trip times, and exports JSON and text reports.

This version organizes the uploaded course project and fixes DNS-flag handling, report aggregation, repeated-response graph edges, TCP response classification and interruption handling. Changes and verification limits are recorded in [docs/REVIEW.md](docs/REVIEW.md). Live probing and browser rendering have not been verified during this review.

## Implemented functionality

- Read multiple destination IP addresses or hostnames from a text file.
- Send ICMP echo, UDP and TCP SYN probes at successive TTL values.
- Record protocol, destination, TTL, reply IP, reverse-DNS name, RTT and response status for each completed probe.
- Repeat the three-protocol series a configurable number of times at each hop.
- Disable reverse lookups with `--no-dns`; target hostnames still require forward resolution.
- Stop a destination trace after a reported destination response, the maximum TTL, or three consecutive hops without a non-timeout response.
- Export every stored probe, including explicit probe errors, to JSON; calculate text-report RTT means across all repetitions for each protocol.
- Filter an interactive topology graph by destination and protocol, toggle hostnames, and inspect node/edge details.

Probes currently run **sequentially**, in ICMP → UDP → TCP order for each repetition. The original README's concurrency claim does not describe this implementation.

## How the components fit together

1. `parser.py` reads CLI settings, and `main.py` loads the target list.
2. `tracer.py` iterates over TTL values and calls the three packet builders in `probes.py`.
3. `dns_utils.py` attempts reverse lookups for responding addresses.
4. `exporter.py` writes `output/results.json` and `output/results.txt`.
5. `frontEnd/app.js` transforms the JSON into graph data; `graph.js` renders it with vis-network.

The graph groups responses by TTL and protocol before constructing inferred links. Repeated replies at one TTL do not become extra hops. Dashed edges flag missing-hop gaps or alternative-hop ambiguity. These links are not verified physical network connections.

## Repository contents

| Path | Purpose |
| --- | --- |
| `main.py` | Load targets and orchestrate tracing/export |
| `parser.py` | TTL, timeout, port, repetition and other CLI settings |
| `probes.py` | Scapy packet construction, send/receive and response classification |
| `tracer.py` | TTL progression, stop conditions and terminal summaries |
| `dns_utils.py` | Reverse-DNS lookup helper |
| `exporter.py` | Raw JSON, tabular text and per-hop aggregate statistics |
| `frontEnd/index.html` | Explorer interface and external vis-network script |
| `frontEnd/app.js` | Load results and transform observations into graph nodes/edges |
| `frontEnd/data.js` | Group observations by TTL/protocol and mark inferred-link uncertainty |
| `frontEnd/graph.js` | Filtering, aggregation, layout and detail inspection |
| `frontEnd/style.css` | Explorer styling and responsive layout |
| `targets.txt` | Original example destinations |
| `requirements.txt`, `Makefile` | Tested Scapy version and virtual-environment run/test targets |
| `tests/`, `package.json` | Offline Python and Node regression checks |
| `HOWTO.md` | Setup and execution instructions |
| `docs/REVIEW.md` | Verified checks, implementation gaps and next fixes |
| `docs/original_README.md`, `docs/original_HOWTO.md` | Unedited original documentation |
| `docs/original_structure.png` | Original proposed directory sketch; actual source layout differs |

## Quick start

The original instructions recommend Python 3.12+. Packet probing requires the privileges needed by Scapy on the host. The following commands assume a Unix-like environment and are intended to be run from the project root.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Run against destinations selected in targets.txt.
# The explicit interpreter keeps the installed virtual-environment dependency available.
sudo .venv/bin/python main.py targets.txt -q 1

# In a separate terminal, serve the project after results have been generated.
.venv/bin/python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/frontEnd/index.html`. The frontend expects `output/results.json`; no recorded output dataset was included in the uploaded archive. Its vis-network dependency is loaded from an external CDN.

For the full option table and output interpretation, see [HOWTO.md](HOWTO.md).

## Tests and verification

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend.test.mjs
```

The suite contains 20 Python tests and 6 Node tests. Python tests use real Scapy packet objects while mocking send/receive, name resolution and waiting; native interface/socket initialization is disabled in the test process. Coverage includes a CLI → trace → JSON/text integration check, DNS toggles, response classification, repeated-query means, errors, partial-result interruption and topology filtering/inference.

No live packets were sent. Host packet privileges, live route accuracy and end-to-end browser rendering remain unverified. The text report's `Timeout %` is a missing-response fraction across probes, not a direct measurement of end-to-end traffic loss. No performance, accuracy or throughput metric is claimed from this archive.
