// SPEND tab extras (Dev A): ownership graph renderer.
// Data comes from the ownership_overlap card: evidence.ownership_graph = {nodes, edges, notes}.
// Related-party edges (related_party: true) are drawn red.

const NODE_STYLE = {
  facility:         { color: { background: '#0f172a', border: '#0f172a' }, font: { color: '#ffffff' }, shape: 'box' },
  operator:         { color: { background: '#e2e8f0', border: '#94a3b8' }, shape: 'box' },
  parent:           { color: { background: '#fde68a', border: '#d97706' }, shape: 'box' },
  supplier:         { color: { background: '#ffffff', border: '#64748b' }, shape: 'box' },
  registered_agent: { color: { background: '#f1f5f9', border: '#cbd5e1' }, shape: 'ellipse', font: { size: 11, color: '#64748b' } },
};

function _tooltip(n) {
  const el = document.createElement('div');
  el.style.cssText = 'font:12px system-ui;max-width:260px;padding:2px';
  const d = n.details || {};
  el.innerHTML =
    `<b>${n.label}</b><br>` +
    `<span style="color:#64748b">${n.type.replace('_', ' ')}${d.state ? ' · ' + d.state : ''}</span>` +
    (d.note ? `<br>${d.note}` : '') +
    (n.illustrative ? `<br><i style="color:#b45309">illustrative name (demo data)</i>` : '');
  return el;
}

window.renderOwnershipGraph = function (container, graph) {
  if (!container) return;
  if (container._network) { container._network.destroy(); container._network = null; }
  if (!graph || !window.vis) { container.innerHTML = '<div class="text-slate-400 text-sm p-4">No ownership graph.</div>'; return; }
  container.innerHTML = '';

  const related = new Set();
  for (const e of graph.edges) if (e.related_party) { related.add(e.from); related.add(e.to); }

  const LEVEL = { parent: 0, operator: 1, registered_agent: 1, facility: 2, supplier: 2 };
  const nodes = graph.nodes.map(n => ({
    id: n.id,
    level: LEVEL[n.type] ?? 1,
    label: n.label + (n.illustrative ? ' *' : ''),
    title: _tooltip(n),
    margin: 10,
    widthConstraint: { maximum: 190 },
    ...(NODE_STYLE[n.type] || {}),
    borderWidth: related.has(n.id) && n.type !== 'facility' ? 3 : 1,
    ...(related.has(n.id) && n.type === 'supplier'
        ? { color: { background: '#fee2e2', border: '#dc2626' } } : {}),
  }));
  const edges = graph.edges.map((e, i) => ({
    id: i, from: e.from, to: e.to, label: e.label, arrows: 'to',
    color: { color: e.related_party ? '#dc2626' : '#94a3b8' },
    width: e.related_party ? 3 : 1,
    dashes: e.type === 'registered_agent',
    font: { size: 11, color: e.related_party ? '#b91c1c' : '#64748b', strokeWidth: 3, align: 'middle' },
  }));

  container._network = new vis.Network(container,
    { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
    {
      // Owners on top (level 0), operators/agents middle, facility + suppliers bottom.
      layout: { hierarchical: { direction: 'UD', sortMethod: 'hubsize', levelSeparation: 120,
                                nodeSpacing: 230 } },
      physics: false,
      interaction: { hover: true, tooltipDelay: 120, zoomView: false },
      nodes: { font: { size: 13, face: 'system-ui' } },
      edges: { smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 } },
    });
  setTimeout(() => container._network && container._network.fit({ animation: false }), 50);
};
