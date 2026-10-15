import test from "node:test";
import assert from "node:assert/strict";
import { transformRawResults } from "../frontEnd/data.js";
import { aggregateEdges, buildVisData, escapeHtml } from "../frontEnd/graph.js";

const reply = (protocol = "ICMP", ip = "192.0.2.254", rtt = 1) => ({
  protocol, reply_ip: ip, reply_name: "router.example", rtt_ms: rtt, status: "TIME_EXCEEDED",
});

test("repeated responses at one TTL never create extra hops or self-loops", () => {
  const probes = ["ICMP", "UDP", "TCP"].flatMap(p => [reply(p), reply(p)]);
  const graph = transformRawResults({ "192.0.2.1": [{ ttl: 1, probes }] });
  assert.equal(graph.nodes.length, 2);
  assert.equal(graph.edges.length, 6);
  assert.ok(graph.edges.every(e => e.from === "src" && e.from !== e.to));
  const edges = aggregateEdges(graph.edges);
  assert.equal(edges.length, 3);
  assert.ok(edges.every(e => e.sample_count === 2));
});

test("TTL alternatives are not chained together and skipped hops are explicit", () => {
  const graph = transformRawResults({ target: [
    { ttl: 4, probes: [reply("ICMP", "192.0.2.1")] },
    { ttl: 1, probes: [reply("ICMP", "192.0.2.20"), reply("ICMP", "192.0.2.21")] },
  ] });
  assert.ok(!graph.edges.some(e => e.from === "192.0.2.20" && e.to === "192.0.2.21"));
  const later = graph.edges.filter(e => e.ttl === 4);
  assert.equal(later.length, 2);
  assert.ok(later.every(e => e.missing_hops === 2 && e.ambiguous && e.inferred));
});

test("timeout-only datasets keep a source node and no inferred edges", () => {
  const graph = transformRawResults({ target: [{ ttl: 1, probes: [{ protocol: "ICMP", reply_ip: null }] }] });
  assert.equal(graph.nodes.length, 1);
  assert.equal(graph.edges.length, 0);
});

test("target/protocol filters and hostname toggle preserve the requested view", () => {
  const graph = transformRawResults({
    one: [{ ttl: 1, probes: [reply("ICMP"), reply("UDP")] }],
    two: [{ ttl: 1, probes: [reply("TCP", "192.0.2.22")] }],
  });
  const view = buildVisData(graph, "one", "UDP", false);
  assert.equal(view.edges.length, 1);
  assert.equal(view.edges[0].raw.protocol, "UDP");
  assert.ok(view.nodes.every(n => !n.label.includes("\n")));
  assert.ok(buildVisData(graph, "one", "UDP", true).nodes.some(n => n.label.includes("router.example")));
});

test("edge aggregation includes zero RTT and marks uncertain links", () => {
  const common = { from: "src", to: "192.0.2.1", protocol: "TCP", target: "target", ttl: 3, status: "REACHED", missing_hops: 2, ambiguous: true };
  const [edge] = aggregateEdges([{ ...common, rtt_ms: 0 }, { ...common, rtt_ms: 10 }]);
  assert.equal(edge.avg_rtt_ms, 5);
  assert.equal(edge.missing_hops, 2);
  assert.equal(edge.ambiguous, true);
  assert.deepEqual(edge.statuses, ["REACHED"]);
});

test("detail text is escaped and malformed result roots are rejected", () => {
  assert.equal(escapeHtml('<img src="x">&'), "&lt;img src=&quot;x&quot;&gt;&amp;");
  for (const invalid of [null, [], "text"]) assert.throws(() => transformRawResults(invalid));
});
