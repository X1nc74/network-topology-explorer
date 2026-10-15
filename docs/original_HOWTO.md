# How to Install and Run the Multi-Protocol Traceroute

## Prerequisites
- Python 3.12 or higher
- Administrator / root privileges for packet probing
- Internet connection

## Installation
1. Install the required dependencies:
   pip install -r requirements.txt

## Execution
1. To run the analyzer on a list of targets:

   sudo python3 main.py targets.txt

2. For a quick demo (fewer queries):
   
   sudo python3 main.py targets.txt -q 1

3. Results will be saved to the output/ directory in both .json (for frontend) and .txt (human-readable report).

4. Launch the frontend visualization

   From the project root directory, start a local HTTP server:
   python -m http.server 8000
   Then open the following page in your browser:
   http://localhost:8000/frontEnd/index.html

5. Using the UI
   Select a target from the Target dropdown
   Select a protocol from the Protocol dropdown
   Toggle hostname visibility if needed
   Click nodes and edges to inspect details
   Notes
   Some hops may timeout because routers or firewalls do not respond to probes
   Different protocols may reveal different paths
   Reverse DNS names may not always be available
   If the browser does not update after rerunning the analyzer, refresh the page.