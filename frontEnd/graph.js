let networkInstance = null;
let currentGraphData = null;

const protocolColors = {
  ICMP: "#7c3aed",
  UDP: "#dc2626",
  TCP: "#0f766e",
};

const nodeColors = {
  source: "#f59e0b",
  destination: "#10b981",
  hop: "#2563eb",
};

function avg(values) {
  if (!values.length) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function buildNodeLabel(node, showHostname) {
  if (!showHostname || !node.hostname) return node.ip;
  return `${node.ip}\n${node.hostname}`;
}

function aggregateEdges(rawEdges) {
  const map = new Map();

  for (const edge of rawEdges) {
    const key = `${edge.from}|${edge.to}|${edge.protocol}`;

    if (!map.has(key)) {
      map.set(key, {
        id: key,
        from: edge.from,
        to: edge.to,
        protocol: edge.protocol,
        targets: new Set(),
        ttls: [],
        rtts: [],
        statuses: [],
      });
    }

    const item = map.get(key);
    item.targets.add(edge.target);
    item.ttls.push(edge.ttl);
    if (typeof edge.rtt_ms === "number") item.rtts.push(edge.rtt_ms);
    if (edge.status) item.statuses.push(edge.status);
  }

  return Array.from(map.values()).map((item) => ({
    id: item.id,
    from: item.from,
    to: item.to,
    protocol: item.protocol,
    targets: Array.from(item.targets),
    ttl_range: `${Math.min(...item.ttls)} - ${Math.max(...item.ttls)}`,
    avg_rtt_ms: item.rtts.length ? Number(avg(item.rtts).toFixed(2)) : null,
    sample_count: item.ttls.length,
    statuses: item.statuses,
  }));
}

function computeLevels(edges) {
  const levels = { src: 0 };
  let changed = true;

  while (changed) {
    changed = false;
    for (const edge of edges) {
      if (levels[edge.from] !== undefined) {
        const nextLevel = levels[edge.from] + 1;
        if (levels[edge.to] === undefined || nextLevel < levels[edge.to]) {
          levels[edge.to] = nextLevel;
          changed = true;
        }
      }
    }
  }

  return levels;
}

function buildVisData(graphData, selectedTarget, selectedProtocol, showHostname) {
  const filteredRawEdges = graphData.edges.filter((edge) => {
    const targetOk = selectedTarget === "ALL" || edge.target === selectedTarget;
    const protocolOk = selectedProtocol === "ALL" || edge.protocol === selectedProtocol;
    return targetOk && protocolOk;
  });

  const aggregatedEdges = aggregateEdges(filteredRawEdges);
  const usedNodeIds = new Set(["src"]);
  aggregatedEdges.forEach((edge) => {
    usedNodeIds.add(edge.from);
    usedNodeIds.add(edge.to);
  });

  const levels = computeLevels(aggregatedEdges);

  const nodes = graphData.nodes
    .filter((node) => usedNodeIds.has(node.id))
    .map((node) => ({
      id: node.id,
      label: buildNodeLabel(node, showHostname),
      shape: node.type === "source" ? "star" : node.type === "destination" ? "diamond" : "dot",
      size: node.type === "source" ? 24 : node.type === "destination" ? 18 : 13,
      color: nodeColors[node.type] || nodeColors.hop,
      level: levels[node.id] ?? 0,
      font: {
        size: 13,
        face: "Inter, Arial, sans-serif",
        strokeWidth: 3,
        strokeColor: "#ffffff",
      },
      raw: node,
    }));

  const edges = aggregatedEdges.map((edge) => ({
    id: edge.id,
    from: edge.from,
    to: edge.to,
    label: edge.protocol,
    arrows: "to",
    width: Math.min(2 + edge.sample_count * 0.5, 5),
    color: {
      color: protocolColors[edge.protocol] || "#94a3b8",
      highlight: protocolColors[edge.protocol] || "#94a3b8",
      hover: protocolColors[edge.protocol] || "#94a3b8",
    },
    font: {
      size: 11,
      color: "#475569",
      background: "rgba(255,255,255,0.85)",
    },
    smooth: {
      enabled: true,
      type: "cubicBezier",
      forceDirection: "horizontal",
      roundness: 0.25,
    },
    raw: edge,
  }));

  return { nodes, edges };
}

function detailBlock(label, value) {
  return `
    <div class="detail-block">
      <div class="detail-key">${label}</div>
      <div class="detail-value">${value}</div>
    </div>
  `;
}

function setDefaultDetails() {
  const details = document.getElementById("details");
  details.className = "details-empty";
  details.textContent = "Select a node or edge to inspect details.";
}

function setDetailsHtml(html) {
  const details = document.getElementById("details");
  details.classList.remove("details-empty");
  details.innerHTML = html;
}

function updateSummary(graphData, selectedTarget, selectedProtocol, visData) {
  const summary = document.getElementById("summary");
  const targetChip = document.getElementById("activeTargetChip");
  const protocolChip = document.getElementById("activeProtocolChip");

  summary.innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Targets</div>
      <div class="stat-value">${graphData.targets.length}</div>
      <div class="stat-sub">Loaded dataset</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Nodes</div>
      <div class="stat-value">${visData.nodes.length}</div>
      <div class="stat-sub">Visible in current view</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Edges</div>
      <div class="stat-value">${visData.edges.length}</div>
      <div class="stat-sub">Aggregated segments</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Mode</div>
      <div class="stat-value">${selectedProtocol}</div>
      <div class="stat-sub">${selectedTarget}</div>
    </div>
  `;

  targetChip.textContent = `Target: ${selectedTarget}`;
  protocolChip.textContent = `Protocol: ${selectedProtocol}`;
}

function attachEvents(network, visData) {
  network.on("click", (params) => {
    if (params.nodes.length > 0) {
      const node = visData.nodes.find((n) => n.id === params.nodes[0])?.raw;
      if (node) {
        setDetailsHtml(
          detailBlock("Type", node.type) +
          detailBlock("IP Address", node.ip) +
          detailBlock("Hostname", node.hostname || "N/A")
        );
      }
      return;
    }

    if (params.edges.length > 0) {
      const edge = visData.edges.find((e) => e.id === params.edges[0])?.raw;
      if (edge) {
        setDetailsHtml(
          detailBlock("Protocol", edge.protocol) +
          detailBlock("Path Segment", `${edge.from} → ${edge.to}`) +
          detailBlock("Targets", edge.targets.join(", ")) +
          detailBlock("TTL Range", edge.ttl_range) +
          detailBlock("Average RTT", edge.avg_rtt_ms !== null ? `${edge.avg_rtt_ms} ms` : "N/A") +
          detailBlock("Samples", String(edge.sample_count)) +
          detailBlock("Statuses", edge.statuses.join(", "))
        );
      }
      return;
    }

    setDefaultDetails();
  });

  network.on("doubleClick", (params) => {
    if (!params.nodes.length && !params.edges.length) {
      network.fit({
        animation: {
          duration: 300,
          easingFunction: "easeInOutQuad",
        },
      });
    }
  });
}

function redraw(selectedTarget = "ALL", selectedProtocol = "ALL", showHostname = true) {
  if (!currentGraphData) return;

  const visData = buildVisData(currentGraphData, selectedTarget, selectedProtocol, showHostname);
  updateSummary(currentGraphData, selectedTarget, selectedProtocol, visData);

  const container = document.getElementById("network");
  const data = {
    nodes: new vis.DataSet(visData.nodes),
    edges: new vis.DataSet(visData.edges),
  };

  const options = {
    physics: false,
    interaction: {
      hover: true,
      dragNodes: true,
      dragView: true,
      zoomView: true,
      navigationButtons: false,
      keyboard: false,
      tooltipDelay: 120,
    },
    layout: {
      hierarchical: {
        enabled: true,
        direction: "LR",
        sortMethod: "directed",
        levelSeparation: 170,
        nodeSpacing: 140,
        treeSpacing: 180,
      },
    },
  };

  if (networkInstance) {
    networkInstance.destroy();
  }

  networkInstance = new vis.Network(container, data, options);
  attachEvents(networkInstance, visData);
  setDefaultDetails();

  setTimeout(() => {
    networkInstance.fit({
      animation: {
        duration: 300,
        easingFunction: "easeInOutQuad",
      },
    });
  }, 50);
}

export function renderGraph(graphData) {
  currentGraphData = graphData;

  const targetFilter = document.getElementById("targetFilter");
  const protocolFilter = document.getElementById("protocolFilter");
  const hostnameToggle = document.getElementById("hostnameToggle");

  targetFilter.innerHTML = `<option value="ALL">All Targets</option>`;
  graphData.targets.forEach((target) => {
    const option = document.createElement("option");
    option.value = target;
    option.textContent = target;
    targetFilter.appendChild(option);
  });

  const rerender = () => {
    redraw(targetFilter.value, protocolFilter.value, hostnameToggle.checked);
  };

  targetFilter.onchange = rerender;
  protocolFilter.onchange = rerender;
  hostnameToggle.onchange = rerender;

  redraw("ALL", "ALL", true);
}