import { renderGraph } from "./graph.js";

const DATA_PATH = "../output/results.json";

async function loadRawResults() {
  const response = await fetch(`${DATA_PATH}?t=${Date.now()}`);
  if (!response.ok) {
    throw new Error(`Failed to load ${DATA_PATH}`);
  }
  return response.json();
}

function normalizeProtocol(protocol) {
  return String(protocol || "").toUpperCase();
}

function getOrCreateNode(nodesMap, ip, hostname = null, type = "hop") {
  if (!ip) return null;

  if (!nodesMap.has(ip)) {
    nodesMap.set(ip, {
      id: ip,
      ip,
      hostname: hostname || null,
      type,
    });
  } else {
    const existing = nodesMap.get(ip);
    if (!existing.hostname && hostname) existing.hostname = hostname;
    if (type === "destination") existing.type = "destination";
  }

  return nodesMap.get(ip);
}

function transformRawResults(rawData) {
  const targets = Object.keys(rawData || {});
  const nodesMap = new Map();
  const edges = [];

  nodesMap.set("src", {
    id: "src",
    ip: "Local Source",
    hostname: "Probe Source",
    type: "source",
  });

  for (const target of targets) {
    const hops = rawData[target] || [];

    const lastSeenByProtocol = {
      ICMP: "src",
      UDP: "src",
      TCP: "src",
    };

    for (const hop of hops) {
      const ttl = hop.ttl;
      const probes = hop.probes || [];

      for (const probe of probes) {
        const protocol = normalizeProtocol(probe.protocol);
        const replyIp = probe.reply_ip;
        const replyName = probe.reply_name;
        const status = probe.status;
        const rttMs = probe.rtt_ms;

        if (!["ICMP", "UDP", "TCP"].includes(protocol)) continue;
        if (!replyIp) continue;

        const nodeType = status === "REACHED" ? "destination" : "hop";
        getOrCreateNode(nodesMap, replyIp, replyName, nodeType);

        edges.push({
          id: `${target}-${protocol}-${ttl}-${lastSeenByProtocol[protocol]}-${replyIp}`,
          from: lastSeenByProtocol[protocol],
          to: replyIp,
          protocol,
          target,
          ttl,
          rtt_ms: rttMs,
          status,
        });

        lastSeenByProtocol[protocol] = replyIp;
      }
    }
  }

  return {
    metadata: {
      generated_at: new Date().toISOString(),
      total_targets: targets.length,
      description: "Transformed from raw traceroute results.json",
    },
    targets,
    nodes: Array.from(nodesMap.values()),
    edges,
  };
}

async function bootstrap() {
  try {
    const rawData = await loadRawResults();
    const graphData = transformRawResults(rawData);

    console.log("Raw Results:", rawData);
    console.log("Graph Data:", graphData);

    renderGraph(graphData);
  } catch (error) {
    console.error(error);
    document.body.innerHTML = `
      <div style="padding:24px;font-family:sans-serif;">
        <h2>Failed to load data</h2>
        <p>${error.message}</p>
        <p>Make sure you are serving the project with a local HTTP server.</p>
      </div>
    `;
  }
}

bootstrap();