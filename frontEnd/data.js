const PROTOCOLS = ["ICMP", "UDP", "TCP"];

function getOrCreateNode(nodes, ip, hostname, type) {
  if (!nodes.has(ip)) nodes.set(ip, { id: ip, ip, hostname: hostname || null, type });
  const node = nodes.get(ip);
  if (!node.hostname && hostname) node.hostname = hostname;
  if (type === "destination") node.type = "destination";
}

export function transformRawResults(rawData) {
  if (!rawData || typeof rawData !== "object" || Array.isArray(rawData)) {
    throw new Error("Expected a results object keyed by destination.");
  }
  const targets = Object.keys(rawData);
  const nodes = new Map([["src", {
    id: "src", ip: "Local Source", hostname: "Probe Source", type: "source",
  }]]);
  const edges = [];

  for (const target of targets) {
    const byTTL = new Map();
    for (const hop of rawData[target] || []) {
      if (!Number.isInteger(hop.ttl) || hop.ttl < 1) continue;
      if (!byTTL.has(hop.ttl)) byTTL.set(hop.ttl, []);
      byTTL.get(hop.ttl).push(...(hop.probes || []));
    }
    const previous = new Map(PROTOCOLS.map(p => [p, { ttl: 0, ips: ["src"] }]));

    for (const [ttl, probes] of [...byTTL].sort((a, b) => a[0] - b[0])) {
      for (const protocol of PROTOCOLS) {
        const replies = new Map();
        for (const probe of probes) {
          if (String(probe.protocol || "").toUpperCase() !== protocol || !probe.reply_ip) continue;
          const ip = probe.reply_ip;
          getOrCreateNode(nodes, ip, probe.reply_name, probe.status === "REACHED" ? "destination" : "hop");
          if (!replies.has(ip)) replies.set(ip, []);
          replies.get(ip).push(probe);
        }
        if (!replies.size) continue;

        // Complete the whole TTL group before advancing the previous-hop state.
        // Repeated probes at one TTL never become hops between one another.
        const prior = previous.get(protocol);
        const ambiguous = prior.ips.length > 1 || replies.size > 1;
        for (const [ip, samples] of replies) {
          for (const from of prior.ips) {
            samples.forEach((sample, index) => edges.push({
              id: JSON.stringify([target, protocol, ttl, from, ip, index]),
              from, to: ip, protocol, target, ttl,
              rtt_ms: sample.rtt_ms, status: sample.status,
              missing_hops: Math.max(0, ttl - prior.ttl - 1),
              ambiguous, inferred: true,
            }));
          }
        }
        previous.set(protocol, { ttl, ips: [...replies.keys()] });
      }
    }
  }
  return {
    metadata: {
      generated_at: new Date().toISOString(), total_targets: targets.length,
      description: "Inferred links between responding TTL groups; not verified physical links",
    },
    targets, nodes: [...nodes.values()], edges,
  };
}
