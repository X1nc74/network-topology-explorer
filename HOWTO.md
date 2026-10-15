# Setup and usage

Run the commands from the repository root. The project uses Python 3.12 or later and pins the tested Scapy version to `2.8.0`. Node is needed only for the offline frontend tests; the explorer itself runs in a browser.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Generate a trace

Put one destination IP address or hostname per line in a text file. `targets.txt` contains the original examples.

```bash
# One ICMP/UDP/TCP series per TTL.
sudo .venv/bin/python main.py targets.txt -q 1

# Display command-line options without starting a trace.
.venv/bin/python main.py --help
```

The `sudo` example uses the virtual environment's interpreter explicitly. Packet privileges and Scapy platform requirements must be satisfied on the machine running the probes. Check the destination list before running; the command sends real network packets.

| Option | Default | Current behavior |
| --- | --- | --- |
| `input_file` | Required | Text file with nonempty destination lines |
| `-m`, `--max_ttl` | `30` | Last TTL to attempt |
| `-M`, `--min_ttl` | `1` | First TTL to attempt |
| `-p`, `--port` | `80` | Destination port for both UDP and TCP |
| `-q`, `--queries` | `3` | Number of ICMP/UDP/TCP series at each hop |
| `-t`, `--timeout` | `2` | Positive receive timeout in seconds per probe; fractional values accepted |
| `-s`, `--size` | `56` | Payload bytes appended to each packet; headers are additional |
| `-w`, `--wait` | `0.1` | Delay in seconds after each completed probe |
| `-n`, `--no-dns` | Disabled | Skip reverse lookups; destination hostnames still need forward resolution |

The parser validates TTLs (1–255), ports (1–65535), positive query counts/timeouts, finite non-negative waits, payload sizes (0–65495) and TTL ordering. Probes are sequential; each query series makes three send/receive calls.

A trace finishes the current hop and stops when any probe is classified as having reached the destination, after three consecutive hops without replies, or when the TTL limit is exhausted. Ctrl+C saves completed observations, including a partly collected current hop, skips remaining destinations and exits with code `130`. Local probe/target errors produce exit code `1`; ordinary response timeouts are retained as observations. Results cannot be saved if the process is forcibly terminated or the output directory is unwritable.

## Inspect output

- `output/results.json` preserves the returned per-probe records grouped by destination and TTL.
- `output/results.txt` includes mean RTTs per protocol and per-hop attempt, timeout and error counts.

For `-q` greater than one, each protocol column averages all non-missing RTT samples at that hop, including valid zero values. The JSON preserves every stored probe, with `ERROR` records for local probe exceptions. The report's timeout percentage combines protocols and does not establish end-to-end traffic loss.

## Open the topology explorer

After generating results, run:

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1
```

Visit `http://127.0.0.1:8000/frontEnd/index.html`. Select a destination or protocol, toggle hostname labels, and click a node or edge for details. Refresh after generating new results. The frontend fetches `../output/results.json` and loads vis-network from an external CDN.

No example output was supplied in the archive. Opening the frontend before generating results will show a data-loading error. Repeated same-hop responses are grouped before links are constructed. Dashed links indicate gaps or alternative-hop ambiguity; edge details explain the inference. See [docs/REVIEW.md](docs/REVIEW.md).

## Convenience targets and tests

`make install` creates `.venv` and installs the pinned dependency. `make run` uses that environment's interpreter under `sudo`. `make serve` starts the local server, and `make test` runs both suites (Node must be installed). `make clean` deletes generated JSON and text files in `output/`.

The equivalent test commands are:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend.test.mjs
```

The tests do not require administrator privileges or live network access. They use real Scapy packet objects, mock all probe I/O, and disable Scapy's native interface/socket initialization in the test process.
