"""Offline regression checks: Scapy packets are real; all I/O is mocked."""

import contextlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

# Offline tests must not enumerate interfaces or open native sockets on import.
# Packet construction and dissection still use the real Scapy classes.
from scapy.config import conf
conf.route_autoload = False
conf.route6_autoload = False
with patch("scapy.config._set_conf_sockets"):
    from scapy.all import ICMP, IP, TCP, UDP, Raw

import dns_utils
import exporter
import main
from parser import parse_arguments
import probes
import tracer

TARGET = "192.0.2.1"
ROUTER = "192.0.2.254"


def observation(protocol="ICMP", status="TIME_EXCEEDED", rtt=1.0):
    responding = status not in ("TIMEOUT", "ERROR")
    return {
        "protocol": protocol, "target_ip": TARGET, "ttl": 1,
        "reply_ip": ROUTER if responding else None, "reply_name": None,
        "rtt_ms": rtt if responding else None, "status": status,
    }


class ProbeTests(unittest.TestCase):
    def call_probe(self, protocol, **extra):
        fn = getattr(probes, f"send_{protocol.lower()}_probe")
        args = (TARGET, 7, 4444, 0.2) if protocol != "ICMP" else (TARGET, 7, 0.2)
        return fn(*args, packet_size=3, **extra)

    def test_no_dns_for_all_protocols_and_packet_parameters(self):
        replies = {
            "ICMP": IP(src=TARGET) / ICMP(type=0),
            "UDP": IP(src=TARGET) / ICMP(type=3, code=3),
            "TCP": IP(src=TARGET) / TCP(flags="SA"),
        }
        for protocol, reply in replies.items():
            with self.subTest(protocol=protocol), patch("probes.sr1", return_value=reply) as send, patch("probes.resolve_ip") as dns:
                result = self.call_probe(protocol, resolve_dns=False)
                self.assertEqual(result["status"], "REACHED")
                self.assertIsNone(result["reply_name"])
                dns.assert_not_called()
                packet = send.call_args.args[0]
                self.assertEqual(packet[IP].ttl, 7)
                self.assertEqual(len(packet[Raw].load), 3)
                if protocol != "ICMP":
                    self.assertEqual(packet[UDP if protocol == "UDP" else TCP].dport, 4444)

    def test_enabled_dns_and_zero_rtt_are_preserved(self):
        with patch("probes.sr1", return_value=IP(src=TARGET) / ICMP(type=0)), patch("probes.resolve_ip", return_value="destination.example") as dns, patch("probes.time.perf_counter", side_effect=[2.0, 2.0]):
            result = self.call_probe("ICMP")
        dns.assert_called_once_with(TARGET)
        self.assertEqual(result["reply_name"], "destination.example")
        self.assertEqual(result["rtt_ms"], 0.0)

    def test_timeouts_have_no_reply_or_dns(self):
        for protocol in ("ICMP", "UDP", "TCP"):
            with self.subTest(protocol=protocol), patch("probes.sr1", return_value=None), patch("probes.resolve_ip") as dns:
                result = self.call_probe(protocol)
                self.assertEqual(result["status"], "TIMEOUT")
                self.assertIsNone(result["rtt_ms"])
                dns.assert_not_called()

    def test_time_exceeded_takes_priority_over_quoted_tcp(self):
        reply = IP(src=ROUTER) / ICMP(type=11) / IP(dst=TARGET) / TCP(flags="SA")
        for protocol in ("ICMP", "UDP", "TCP"):
            with self.subTest(protocol=protocol), patch("probes.sr1", return_value=reply):
                self.assertEqual(self.call_probe(protocol, resolve_dns=False)["status"], "TIME_EXCEEDED")

    def test_tcp_requires_syn_ack_or_rst(self):
        for flags, expected in [("A", "UNKNOWN"), ("S", "UNKNOWN"), ("SA", "REACHED"), ("R", "REACHED"), ("RA", "REACHED")]:
            with self.subTest(flags=flags), patch("probes.sr1", return_value=IP(src=TARGET) / TCP(flags=flags)):
                self.assertEqual(self.call_probe("TCP", resolve_dns=False)["status"], expected)

    def test_other_sources_do_not_mark_destination_reached(self):
        replies = {"ICMP": ICMP(type=0), "UDP": ICMP(type=3, code=3), "TCP": TCP(flags="SA")}
        for protocol, layer in replies.items():
            with self.subTest(protocol=protocol), patch("probes.sr1", return_value=IP(src=ROUTER) / layer):
                self.assertNotEqual(self.call_probe(protocol, resolve_dns=False)["status"], "REACHED")

    def test_unreachable_is_distinct_from_timeout(self):
        with patch("probes.sr1", return_value=IP(src=ROUTER) / ICMP(type=3, code=1)):
            self.assertEqual(self.call_probe("UDP", resolve_dns=False)["status"], "UNREACHABLE")

    def test_reverse_dns_failure_and_interrupt(self):
        with patch("dns_utils.socket.gethostbyaddr", side_effect=socket.herror("no PTR")):
            self.assertIsNone(dns_utils.resolve_ip(TARGET))
        with patch("dns_utils.socket.gethostbyaddr", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                dns_utils.resolve_ip(TARGET)


class TraceTests(unittest.TestCase):
    def test_cli_to_json_workflow_with_real_packets_and_mocked_io(self):
        replies = [IP(src=ROUTER) / ICMP(type=11) for _ in range(3)] + [
            IP(src=TARGET) / ICMP(type=0),
            IP(src=TARGET) / ICMP(type=3, code=3),
            IP(src=TARGET) / TCP(flags="SA"),
        ]
        with tempfile.TemporaryDirectory() as temp, contextlib.chdir(temp):
            Path("targets.txt").write_text(TARGET + "\n")
            with patch("tracer.socket.gethostbyname", return_value=TARGET), patch("tracer.time.sleep"), patch("probes.sr1", side_effect=replies) as send, patch("probes.resolve_ip") as dns, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(["targets.txt", "-q", "1", "-m", "3", "-n"]), 0)
            self.assertEqual(send.call_count, 6)
            dns.assert_not_called()
            data = json.loads(Path("output/results.json").read_text())
            self.assertEqual(len(data[TARGET]), 2)
            self.assertTrue(all(p["status"] == "REACHED" for p in data[TARGET][-1]["probes"]))
            self.assertIn("ICMP mean", Path("output/results.txt").read_text())

    def run_with(self, results, argv=None):
        args = parse_arguments(["targets.txt", "-q", "1", "-m", "4", "-w", "0", "-n"] + (argv or []))
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(patch("tracer.socket.gethostbyname", return_value=TARGET))
            stack.enter_context(patch("tracer.time.sleep"))
            mocks = [stack.enter_context(patch("tracer.send_" + p.lower() + "_probe", side_effect=results[p] if isinstance(results[p], BaseException) else None, return_value=results[p])) for p in ("ICMP", "UDP", "TCP")]
            return tracer.run_trace("destination.example", args), mocks

    def test_dns_flag_propagates_to_all_repetitions(self):
        results = {p: observation(p) for p in ("ICMP", "UDP", "TCP")}
        hops, mocks = self.run_with(results, ["-m", "1", "-q", "2"])
        self.assertEqual(len(hops[0]["probes"]), 6)
        for mock in mocks:
            self.assertEqual(mock.call_count, 2)
            self.assertTrue(all(c.kwargs["resolve_dns"] is False for c in mock.call_args_list))

    def test_stop_after_three_unanswered_hops(self):
        results = {p: observation(p, "TIMEOUT") for p in ("ICMP", "UDP", "TCP")}
        hops, _ = self.run_with(results, ["-m", "30"])
        self.assertEqual([h["ttl"] for h in hops], [1, 2, 3])

    def test_reached_stops_before_next_ttl(self):
        results = {p: observation(p, "REACHED" if p == "TCP" else "TIMEOUT") for p in ("ICMP", "UDP", "TCP")}
        hops, _ = self.run_with(results)
        self.assertEqual(len(hops), 1)

    def test_probe_errors_remain_in_the_result(self):
        results = {"ICMP": PermissionError("raw socket unavailable"), "UDP": observation("UDP", "TIMEOUT"), "TCP": observation("TCP", "TIMEOUT")}
        hops, _ = self.run_with(results, ["-m", "1"])
        self.assertEqual(len(hops[0]["probes"]), 3)
        self.assertEqual(hops[0]["probes"][0]["status"], "ERROR")
        self.assertIn("raw socket", hops[0]["probes"][0]["error"])

    def test_interrupt_keeps_current_partial_hop(self):
        results = {"ICMP": observation(), "UDP": KeyboardInterrupt(), "TCP": observation("TCP")}
        with self.assertRaises(tracer.TraceInterrupted) as caught:
            self.run_with(results)
        self.assertEqual(len(caught.exception.results), 1)
        self.assertEqual(len(caught.exception.results[0]["probes"]), 1)

    def test_cli_interrupt_saves_and_skips_later_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            targets = Path(temp) / "targets.txt"
            targets.write_text("192.0.2.1\n192.0.2.2\n")
            partial = [{"ttl": 1, "probes": [observation()]}]
            with patch("main.run_trace", side_effect=tracer.TraceInterrupted(partial)) as run, patch("main.save_results") as save, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main([str(targets)]), 130)
            run.assert_called_once()
            self.assertEqual(save.call_args.args[0], {"192.0.2.1": partial})

    def test_unresolvable_target_does_not_abort_other_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            targets = Path(temp) / "targets.txt"
            targets.write_text("bad.example\n192.0.2.1\n")
            with patch("main.run_trace", side_effect=[socket.gaierror("not found"), []]) as run, patch("main.save_results") as save, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main.main([str(targets)]), 1)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(set(save.call_args.args[0]), {"bad.example", "192.0.2.1"})


class ExportTests(unittest.TestCase):
    def export(self, data):
        with tempfile.TemporaryDirectory() as temp:
            txt = Path(temp) / "text" / "report.txt"
            js = Path(temp) / "json" / "report.json"
            with contextlib.redirect_stdout(io.StringIO()):
                exporter.save_results(data, txt, js)
            self.assertEqual(json.loads(js.read_text()), data)
            return txt.read_text()

    def test_all_repetitions_contribute_to_protocol_means(self):
        samples = [observation(p, rtt=v) for values in [(1, 2, 3), (11, 12, 13)] for p, v in zip(("ICMP", "UDP", "TCP"), values)]
        text = self.export({TARGET: [{"ttl": 1, "probes": samples}]})
        row = next(line for line in text.splitlines() if ROUTER in line and "6.00ms" in line)
        self.assertIn("7.00ms", row)
        self.assertIn("8.00ms", row)

    def test_zero_rtt_missing_protocols_errors_and_empty_hops(self):
        samples = [observation(rtt=0.0), observation("UDP", "TIMEOUT"), observation("TCP", "ERROR")]
        text = self.export({TARGET: [{"ttl": 1, "probes": samples}, {"ttl": 2, "probes": []}]})
        self.assertIn("0.00ms", text)
        self.assertIn("33.3%", text)
        self.assertIn("N/A", text)
        self.assertIn("Errors", text)


class ParserTests(unittest.TestCase):
    def test_fractional_timeout_zero_wait_and_dns_flag(self):
        args = parse_arguments(["targets.txt", "-t", "0.25", "-w", "0", "-n", "-s", "0"])
        self.assertEqual(args.timeout, 0.25)
        self.assertTrue(args.no_dns)

    def test_invalid_ranges_and_nonfinite_values(self):
        cases = [["-q", "0"], ["-q", "-1"], ["-p", "0"], ["-p", "65536"], ["-M", "0"], ["-m", "256"], ["-M", "3", "-m", "2"], ["-t", "0"], ["-t", "nan"], ["-t", "inf"], ["-w", "-1"], ["-w", "nan"], ["-s", "-1"], ["-s", "65496"]]
        for argv in cases:
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    parse_arguments(["targets.txt"] + argv)
                self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
