/* Screen canvas on React Flow (@xyflow/react).
   Data arrives from build_canvas.py in window.__CANVAS_DATA__ with coordinates already
   assigned. There is no auto-layout here: the graph comes from the frontend code, and the
   order of screens must match the way a user actually walks through them. */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ReactFlow, ReactFlowProvider, Background, MiniMap, Panel, Handle, Position,
  useReactFlow, useStore,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
// Fira Sans is the design font. Bundled locally and inlined: the page opens from disk with
// no network, and falling back to a system font breaks the metrics.
import '@fontsource/fira-sans/cyrillic-400.css';
import '@fontsource/fira-sans/cyrillic-500.css';
import '@fontsource/fira-sans/cyrillic-600.css';
import '@fontsource/fira-sans/latin-400.css';
import '@fontsource/fira-sans/latin-500.css';
import '@fontsource/fira-sans/latin-600.css';
import './tokens.css';
import './styles.css';

const DATA = window.__CANVAS_DATA__;
const KIND_GROUP = {
  sidebar: 'nav', routerLink: 'nav', navigate: 'nav', manual: 'nav',
  'row-click': 'nav', 'row-action': 'nav', tab: 'tab', state: 'state', back: 'back',
};
const KIND_COLOR = { nav: '#2196f3', tab: '#16a34a', state: '#ca8a04', back: '#9aa0a8' };
const KIND_LABEL = { nav: 'navigation', tab: 'tabs', state: 'states', back: 'back' };

const byId = new Map(DATA.nodes.map((n) => [n.id, n]));
const hidden = { opacity: 0, width: 1, height: 1, minWidth: 1, minHeight: 1, border: 0 };


/* ---------- icons ---------- */
const Ico = {
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  fit: 'M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M3 16v3a2 2 0 0 0 2 2h3',
  filter: 'M3 5h18M6 12h12M10 19h4',
  groups: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  map: 'M9 4 3 7v13l6-3 6 3 6-3V4l-6 3-6-3zM9 4v13M15 7v13',
  close: 'M18 6 6 18M6 6l12 12',
};

function Icon({ d, size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

function Tip({ children, kbd }) {
  return <span className="tooltip">{children}{kbd && <kbd>{kbd}</kbd>}</span>;
}

/* Popover above a button: long lists take no room in the dock. */
function Pop({ open, onClose, children, width = 260 }) {
  if (!open) return null;
  return (
    <>
      <div className="pop-scrim" onClick={onClose} />
      <div className="pop" style={{ width }} onClick={(e) => e.stopPropagation()}>{children}</div>
    </>
  );
}

/* ---------- nodes ---------- */

const ZONE_COLOR = ['gf-blue', 'gf-green', 'gf-purple', 'gf-yellow', 'gf-pink', 'gf-gray'];

function ZoneNode({ data }) {
  return (
    <div className={cx('zone', data.color)}>
      <div className="bar">
        <span className="dot" />
        <span className="label">{data.title}</span>
        <span className="cnt">{data.count} {data.count === 1 ? 'screen' : 'screens'}</span>
      </div>
    </div>
  );
}

function ScreenNode({ data }) {
  // A small preview on the overview, the full frame once zoomed in: otherwise the board is
  // either unreadable up close or holds every full-size frame in memory at once.
  const sharp = useStore((s) => s.transform[2] >= DATA.zoom_sharp);
  const n = data.node;
  const notScreen = n.kind === 'redirect' || n.kind === 'global' || n.id === '/' || n.id === '/logout';
  const src = sharp && n.shot_full ? n.shot_full : n.shot;
  return (
    <div className={cx('card', n.layer === 'state' && 'state', notScreen && 'nos',
      data.isSel && 'sel', data.dimmed && 'dim')}>
      <Handle type="target" position={Position.Left} style={hidden} />
      <div className={cx('shot', n.cropped && 'cut')} style={{ height: n.img_h || 0 }}>
        {src
          ? <img src={src} alt="" draggable={false} />
          : <div className="ph">{notScreen ? 'not a screen — a navigation point' : 'no frame'}</div>}
      </div>
      <div className="pins">
        {n.roles.map((r) => <span key={r} className="pin role">{r}</span>)}
        {!n.shot && !notScreen && <span className="pin gap">no frame</span>}
        {n.cropped && <span className="pin">frame cropped</span>}
        {n.comments.length > 0 && <span className="pin note">{n.comments.length}</span>}
      </div>
      <div className="meta">
        <div className="ttl">{n.state || n.title}</div>
        <div className="sub">{n.shot_borrowed ? `frame: ${n.shot_borrowed}` : n.url}</div>
      </div>
      <Handle type="source" position={Position.Right} style={hidden} />
    </div>
  );
}

function NoteNode({ data }) {
  const c = data.comment;
  return (
    <div className={cx('sticky', c.kind === 'finding' && 'finding', data.dimmed && 'dim')}>
      <b>{[c.kind || 'note', c.author, c.date].filter(Boolean).join(' · ')}</b>
      {c.text}
    </div>
  );
}

const nodeTypes = { zone: ZoneNode, screen: ScreenNode, note: NoteNode };

function ZoneLabels() {
  const [tx, ty, zoom] = useStore((s) => s.transform);
  if (zoom >= 0.42) return null;
  return (
    <div className="zlabels">
      {DATA.zones.map((z, i) => {
        const x = z.x * zoom + tx, y = z.y * zoom + ty;
        z.color = z.color || ZONE_COLOR[i % ZONE_COLOR.length];
        return (
          <span key={z.family} className={z.color} style={{ left: Math.max(8, x), top: Math.max(8, y - 34) }}>
            <i className="dot-sm" style={{ background: 'var(--gf-dot)' }} />{z.title}
          </span>
        );
      })}
    </div>
  );
}

/* ---------- building the graph ---------- */

function buildNodes() {
  const out = DATA.zones.map((z, i) => ({
    id: `zone:${z.family}`,
    type: 'zone',
    position: { x: z.x, y: z.y },
    width: z.w, height: z.h,
    style: { width: z.w, height: z.h },
    data: { title: z.title, count: z.count, color: ZONE_COLOR[i % ZONE_COLOR.length] },
    draggable: false, selectable: false, connectable: false,
    zIndex: 0,
  }));
  for (const n of DATA.nodes) {
    out.push({
      id: n.id,
      type: 'screen',
      position: { x: n.x, y: n.y },
      width: n.w, height: n.h,
      style: { width: n.w, height: n.h },
      data: { node: n, dimmed: false },
      draggable: false, connectable: false,
      zIndex: 2,
    });
    let noteY = n.y;
    n.comments.forEach((c, i) => {
      const h = c.h || 152;              // build_canvas.py computes the height from the text length
      const y = noteY;
      noteY += h + 14;
      out.push({
        id: `note:${n.id}:${i}`,
        type: 'note',
        position: { x: n.x + n.w + 18, y },
        width: 258, height: h,
        style: { width: 258, height: h },
        data: { comment: c, of: n.id, dimmed: false },
        draggable: false, selectable: false, connectable: false,
        zIndex: 2,
      });
    });
  }
  return out;
}

function buildEdges() {
  return DATA.edges.map((e, i) => {
    const k = KIND_GROUP[e.kind] || 'nav';
    return {
      id: `e${i}`,
      source: e.from, target: e.to,
      style: { stroke: KIND_COLOR[k], strokeWidth: 2, opacity: .5,
        strokeDasharray: k === 'back' ? '6 5' : undefined },
      data: { kind: k, trigger: e.trigger },
      zIndex: 1,
    };
  });
}

/* ---------- the explanation panel ---------- */

function Details({ id, onClose, onJump }) {
  const n = id ? byId.get(id) : null;
  const outs = useMemo(() => (n ? DATA.edges.filter((e) => e.from === n.id) : []), [n]);
  const ins = useMemo(() => (n ? DATA.edges.filter((e) => e.to === n.id) : []), [n]);
  return (
    <aside className={cx('panel', 'float', n && 'open')}>
      {n && (
        <>
          <div className="ph">
            <button className="close" onClick={onClose}>×</button>
            <h2>{n.title}</h2>
            <code>{n.url}{n.state ? `  ·  ${n.state}` : ''}</code>
          </div>
          <div className="body">
            {n.comments.length > 0 && <h3>Comments</h3>}
            {n.comments.map((c, i) => (
              <div key={i} className={cx('cmt', c.kind === 'finding' && 'finding')}>
                <div className="who">{[c.kind || 'note', c.author, c.date].filter(Boolean).join(' · ')}</div>
                {c.text}
              </div>
            ))}
            {n.cropped && (
              <>
                <h3>The frame on this card</h3>
                <div>The frame is taller than the card and cropped at the bottom — open it in full below.</div>
              </>
            )}
            {n.shot_borrowed && (
              <>
                <h3>The frame on this card</h3>
                <div>This screen has no frame of its own — showing the state “{n.shot_borrowed}”.</div>
              </>
            )}
            {n.flags.length > 0 && <h3>Flagged in the frame</h3>}
            {n.flags.map((f, i) => <div key={i} className="flagbox">{f}</div>)}
            {n.notes.map((note, i) => (
              <React.Fragment key={i}>
                <h3>{note.term}</h3>
                {note.text && <div>{note.text}</div>}
                {note.items.length > 0 && <ul>{note.items.map((it, j) => <li key={j}>{it}</li>)}</ul>}
              </React.Fragment>
            ))}
            {outs.length > 0 && <h3>Leads to</h3>}
            {outs.map((e, i) => <Jump key={i} to={e.to} trigger={e.trigger} onJump={onJump} />)}
            {ins.length > 0 && <h3>Reached from</h3>}
            {ins.map((e, i) => <Jump key={i} to={e.from} trigger={e.trigger} onJump={onJump} />)}
            <h3>Sources</h3>
            <ul>
              {n.storyboard && <li><a href={n.storyboard} target="_blank" rel="noreferrer">frame and explanation in the storyboard</a></li>}
              {n.shot_full && <li><a href={n.shot_full} target="_blank" rel="noreferrer">full-size frame</a></li>}
              {n.source && <li>route: <code>{n.source}</code></li>}
            </ul>
          </div>
        </>
      )}
    </aside>
  );
}

function Jump({ to, trigger, onJump }) {
  const t = byId.get(to);
  return (
    <button className="jump" onClick={() => onJump(to)}>
      {t ? (t.state || t.title) : to}
      <div className="t">{trigger}</div>
    </button>
  );
}


/* Zoom lives in its own vertical dock at the right edge so it does not crowd the main dock. */
function ZoomDock({ showMap, onToggleMap }) {
  const flow = useReactFlow();
  const zoom = useStore((s) => s.transform[2]);
  const pct = Math.round(zoom * 100);
  const [draft, setDraft] = useState(null);

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = e.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === '+' || e.key === '=') flow.zoomIn({ duration: 200 });
      else if (e.key === '-' || e.key === '_') flow.zoomOut({ duration: 200 });
      else if (e.key === '!' || (e.shiftKey && e.key === '1')) flow.fitView({ padding: .06, duration: 500 });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [flow]);

  const apply = (v) => {
    const n = parseInt(v, 10);
    if (!Number.isNaN(n)) flow.zoomTo(Math.min(400, Math.max(3, n)) / 100, { duration: 200 });
  };

  return (
    <div className="zoom-dock float" role="toolbar" aria-orientation="vertical" aria-label="Zoom">
      <button className="ico-btn" onClick={() => flow.zoomIn({ duration: 200 })} aria-label="Zoom in">
        <Icon d={Ico.plus} /><Tip kbd="+">Zoom in</Tip>
      </button>
      <input className="pct" aria-label="Zoom, %"
        value={draft ?? `${pct}%`} inputMode="numeric"
        onFocus={(e) => { setDraft(String(pct)); requestAnimationFrame(() => e.target.select()); }}
        onChange={(e) => { const m = e.target.value.match(/\d+/); setDraft(m ? m[0] : ''); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { apply(draft ?? pct); setDraft(null); e.currentTarget.blur(); }
          else if (e.key === 'Escape') { setDraft(null); e.currentTarget.blur(); }
        }}
        onBlur={() => setDraft(null)} />
      <button className="ico-btn" onClick={() => flow.zoomOut({ duration: 200 })} aria-label="Zoom out">
        <Icon d={Ico.minus} /><Tip kbd="−">Zoom out</Tip>
      </button>
      <div className="dock-divider" />
      <button className="ico-btn" onClick={() => flow.fitView({ padding: .06, duration: 500 })} aria-label="Fit to view">
        <Icon d={Ico.fit} /><Tip kbd="⇧1">Fit to view</Tip>
      </button>
      <button className="ico-btn" onClick={() => flow.zoomTo(1, { duration: 200 })} aria-label="Zoom to 100%">
        <span className="hundred">1:1</span><Tip>Zoom to 100%</Tip>
      </button>
      <div className="dock-divider" />
      <button className="ico-btn" data-active={showMap || undefined} onClick={onToggleMap} aria-label="Minimap">
        <Icon d={Ico.map} /><Tip>Minimap</Tip>
      </button>
    </div>
  );
}

/* ---------- the app ---------- */

function Canvas() {
  const [nodes, setNodes] = useState(buildNodes);
  const allEdges = useRef(buildEdges());
  const [off, setOff] = useState(() => new Set());
  const [query, setQuery] = useState('');
  const [sel, setSel] = useState(null);
  const [pop, setPop] = useState(null);
  const [showMap, setShowMap] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const flow = useReactFlow();

  const edges = useMemo(() => allEdges.current
    .filter((e) => !off.has(e.data.kind))
    .map((e) => {
      if (!sel) return e;
      const on = e.source === sel || e.target === sel;
      return { ...e, zIndex: on ? 3 : 1,
        style: { ...e.style, opacity: on ? 1 : .1, strokeWidth: on ? 3.5 : 2 } };
    }), [off, sel]);

  const shownNodes = useMemo(() => {
    const q = query.trim().toLowerCase();
    return nodes.map((nd) => {
      if (nd.type === 'zone') return nd;
      const owner = nd.type === 'note' ? byId.get(nd.data.of) : nd.data.node;
      const hit = !q || `${owner.title} ${owner.url} ${owner.state || ''}`.toLowerCase().includes(q);
      const dimmed = !hit;
      const isSel = nd.type === 'screen' && nd.id === sel;
      if (nd.data.dimmed === dimmed && nd.data.isSel === isSel) return nd;
      return { ...nd, data: { ...nd.data, dimmed, isSel } };
    });
  }, [nodes, query, sel]);

  const closeSearch = useCallback(() => { setSearchOpen(false); setQuery(''); }, []);

  const jump = useCallback((id) => {
    const n = byId.get(id);
    if (!n) return;
    setSel(id);
    flow.setCenter(n.x + n.w / 2, n.y + n.h / 2, { zoom: Math.max(flow.getZoom(), .55), duration: 420 });
  }, [flow]);

  const onNodeClick = useCallback((_, nd) => {
    if (nd.type === 'zone') return;
    setSel(nd.type === 'note' ? nd.data.of : nd.id);
  }, []);

  const toZone = (family) => {
    const z = DATA.zones.find((x) => x.family === family);
    if (!z) return;
    flow.fitBounds({ x: z.x, y: z.y, width: z.w, height: z.h }, { padding: .08, duration: 500 });
  };

  const search = (v) => {
    setQuery(v);
    const q = v.trim().toLowerCase();
    if (!q) return;
    const hit = DATA.nodes.find((n) => `${n.title} ${n.url} ${n.state || ''}`.toLowerCase().includes(q));
    if (hit) flow.setCenter(hit.x + hit.w / 2, hit.y + hit.h / 2, { zoom: .6, duration: 420 });
  };

  return (
    <div className={cx('root', sel && 'with-panel')}>
      <ReactFlow
        nodes={shownNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={() => setSel(null)}
        onlyRenderVisibleElements
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        selectionOnDrag={false}
        panOnDrag
        zoomOnDoubleClick={false}
        panActivationKeyCode="Space"
        minZoom={0.03}
        maxZoom={4}
        proOptions={{ hideAttribution: true }}
        defaultViewport={startViewport()}
      >
        <Background bgColor="var(--space-bg)" />
        <ZoneLabels />
        {showMap && (
          <MiniMap pannable zoomable nodeStrokeWidth={0} maskColor="rgba(236,238,242,.72)"
            nodeColor={(nd) => (nd.type === 'zone' ? '#eceff3'
              : nd.type === 'note' ? 'var(--sticky-yellow-shadow)' : 'color-mix(in srgb, var(--Blue) 42%, #fff)')} />
        )}
        <ZoomDock showMap={showMap} onToggleMap={() => setShowMap((v) => !v)} />

        <Panel position="bottom-left" className="dock float">
          {searchOpen ? (
            <div className="dock-search">
              <Icon d={Ico.search} size={15} />
              <input autoFocus className="search" type="search" placeholder="search screens"
                value={query} onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') search(e.currentTarget.value);
                  if (e.key === 'Escape') closeSearch();
                }} />
              <button className="ico-btn sm" onClick={closeSearch} aria-label="Close search">
                <Icon d={Ico.close} size={15} />
              </button>
            </div>
          ) : (
          <>
          <span className="brand" title={`built ${DATA.generated} from commit ${DATA.source.commit}`}>
            {DATA.product}
            <i>{DATA.nodes.length} screens · {DATA.edges.length} transitions</i>
          </span>
          <div className="dock-sep" />

          <div className="pop-anchor">
            <button className="ico-btn" data-active={pop === 'kinds' || off.size > 0 || undefined}
              onClick={() => setPop(pop === 'kinds' ? null : 'kinds')} aria-label="Transition types">
              <Icon d={Ico.filter} /><Tip>Transition types</Tip>
            </button>
            <Pop open={pop === 'kinds'} onClose={() => setPop(null)}>
              <div className="pop-title">Transition types</div>
              {Object.keys(KIND_LABEL).map((k) => (
                <button key={k} className="pop-row" data-on={!off.has(k) || undefined}
                  onClick={() => setOff((prev) => {
                    const next = new Set(prev);
                    next.has(k) ? next.delete(k) : next.add(k);
                    return next;
                  })}>
                  <i className="dot-sm" style={{ background: KIND_COLOR[k] }} />
                  <span>{KIND_LABEL[k]}</span>
                  <em>{allEdges.current.filter((e) => e.data.kind === k).length}</em>
                </button>
              ))}
            </Pop>
          </div>

          <div className="pop-anchor">
            <button className="ico-btn" data-active={pop === 'zones' || undefined}
              onClick={() => setPop(pop === 'zones' ? null : 'zones')} aria-label="Screen groups">
              <Icon d={Ico.groups} /><Tip>Screen groups</Tip>
            </button>
            <Pop open={pop === 'zones'} onClose={() => setPop(null)} width={280}>
              <div className="pop-title">Screen groups</div>
              {DATA.zones.map((z) => (
                <button key={z.family} className="pop-row"
                  onClick={() => { toZone(z.family); setPop(null); }}>
                  <i className={cx('dot-sm', z.color)} style={{ background: 'var(--gf-dot)' }} />
                  <span>{z.title}</span>
                  <em>{z.count}</em>
                </button>
              ))}
            </Pop>
          </div>

          <button className="ico-btn" data-active={query ? true : undefined}
            onClick={() => { setPop(null); setSearchOpen(true); }} aria-label="Search">
            <Icon d={Ico.search} /><Tip>Search screens</Tip>
          </button>
          </>
          )}
        </Panel>
      </ReactFlow>
      <Details id={sel} onClose={() => setSel(null)} onJump={jump} />
    </div>
  );
}

/* The board does not open on the overview: at that zoom the frames are physically unreadable.
   It centres on the screen named by start_at, at a zoom where the UI in the frame is legible. */
function startViewport() {
  const n = byId.get(DATA.start_at) || DATA.nodes[0];
  const zoom = 0.55;
  return {
    x: window.innerWidth / 2 - (n.x + n.w / 2) * zoom,
    y: window.innerHeight / 2 - (n.y + n.h / 2) * zoom,
    zoom,
  };
}

function cx(...xs) { return xs.filter(Boolean).join(' '); }

createRoot(document.getElementById('root')).render(
  <ReactFlowProvider><Canvas /></ReactFlowProvider>,
);
