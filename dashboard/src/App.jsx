import { useState, useCallback, useRef } from "react";

const API_BASE = "http://127.0.0.1:8081";

// ── Icons ──────────────────────────────────────────────────────────────────
const I = {
  Upload:    () => <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  Play:      () => <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21"/></svg>,
  Check:     () => <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>,
  Chevron:   () => <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>,
  File:      () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
  Zap:       () => <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10"/></svg>,
  Download:  () => <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
  Copy:      () => <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>,
  AlertTri:  () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  Bug:       () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="8" y="6" width="8" height="14" rx="4"/><path d="M19 12h2M3 12h2M19 8h2M3 8h2M19 16h2M3 16h2"/><path d="M12 2v4"/></svg>,
  Shield:    () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  TestTube:  () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 2v17.5A2.5 2.5 0 0011.5 22h1a2.5 2.5 0 002.5-2.5V2"/><path d="M7 2h10"/><path d="M9 16h6"/></svg>,
  Route:     () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 000-7h-11a3.5 3.5 0 010-7H15"/><circle cx="18" cy="5" r="3"/></svg>,
  Cluster:   () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="12" cy="12" r="2"/></svg>,
  Lock:      () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>,
  X:         () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  Db:        () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  Cloud:     () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z"/></svg>,
};

// ── Category Definitions ───────────────────────────────────────────────────
const CATEGORY_DEF = {
  fraud: {
    id: "fraud", label: "Fraud Detection", Icon: I.Shield,
    color: "#EF4444", bgColor: "rgba(239,68,68,0.08)",
    desc: "Velocity checks, geo-hop, account enumeration",
    pipelineKeys: ["ingest", "sanitize", "anomaly"],
    configOptions: {
      sensitivity: { label: "Detection Sensitivity", opts: ["High (fewer false negatives)", "Medium (balanced)", "Low (fewer false positives)"] },
      rules: { label: "Rule Set", opts: ["Banking (velocity + geo-hop)", "E-commerce (enumeration)", "Custom"] },
    },
  },
  errors: {
    id: "errors", label: "Error Analysis", Icon: I.Bug,
    color: "#F97316", bgColor: "rgba(249,115,22,0.08)",
    desc: "Cluster similar errors, severity ranking, root cause",
    pipelineKeys: ["ingest", "parse", "embed", "cluster"],
    configOptions: {
      clusters: { label: "Cluster Count", opts: ["Auto-detect (recommended)", "4 clusters", "6 clusters", "8 clusters"] },
      severity: { label: "Severity Filter", opts: ["All levels", "Critical only", "High & Critical", "Exclude info"] },
    },
  },
  testgen: {
    id: "testgen", label: "Test Generation", Icon: I.TestTube,
    color: "#10B981", bgColor: "rgba(16,185,129,0.08)",
    desc: "AI-generated test scenarios from log patterns",
    pipelineKeys: ["ingest", "parse", "sanitize", "embed", "cluster", "anomaly", "journey", "testgen"],
    configOptions: {
      format: { label: "Output Format", opts: ["Gherkin BDD", "Jest / Playwright", "Pytest", "Manual Steps"] },
      coverage: { label: "Coverage Focus", opts: ["All categories", "Fraud only", "Journey paths only"] },
    },
  },
  journeys: {
    id: "journeys", label: "Journey Analysis", Icon: I.Route,
    color: "#A855F7", bgColor: "rgba(168,85,247,0.08)",
    desc: "LSTM user flow modeling, anomalous sequence detection",
    pipelineKeys: ["ingest", "parse", "embed", "journey"],
    configOptions: {
      model: { label: "LSTM Epochs", opts: ["Fast (5 epochs)", "Standard (10 epochs)", "Thorough (25 epochs)"] },
      filter: { label: "Show Journeys", opts: ["All patterns", "Anomalous only", "Normal only"] },
    },
  },
  compliance: {
    id: "compliance", label: "Compliance Check", Icon: I.Lock,
    color: "#FACC15", bgColor: "rgba(250,204,21,0.08)",
    desc: "PCI DSS, GDPR, AML audit trail validation",
    pipelineKeys: ["ingest", "sanitize", "parse"],
    configOptions: {
      framework: { label: "Compliance Framework", opts: ["PCI DSS + GDPR", "PCI DSS only", "GDPR only", "AML / BSA"] },
      pii: { label: "PII Sanitization", opts: ["Enabled — SHA-256", "Enabled — BLAKE2b", "Disabled"] },
    },
  },
  full: {
    id: "full", label: "Full Pipeline", Icon: I.Zap,
    color: "#3B82F6", bgColor: "rgba(59,130,246,0.08)",
    desc: "Complete end-to-end analysis — all modules",
    pipelineKeys: ["ingest", "parse", "sanitize", "embed", "cluster", "anomaly", "journey", "testgen"],
    configOptions: {
      mode: { label: "Analysis Mode", opts: ["Full Pipeline (All Modules)", "Clustering + Anomaly", "Journey + Fraud"] },
      source: { label: "Log Source", opts: ["Uploaded File", "Elasticsearch", "Datadog"] },
    },
  },
};

const PIPELINE_META = {
  ingest:   { label: "Ingesting Logs",        detail: "Reading and validating log records..." },
  parse:    { label: "Parsing & Extracting",  detail: "Extracting endpoints, status codes, error tokens..." },
  sanitize: { label: "PII Sanitization",      detail: "Detecting and tokenizing PII via regex + spaCy NER..." },
  embed:    { label: "Generating Embeddings", detail: "all-MiniLM-L6-v2 encoding messages → 384-dim vectors..." },
  cluster:  { label: "Clustering Events",     detail: "TF-IDF + MiniBatchKMeans (k=auto)..." },
  anomaly:  { label: "Anomaly Detection",     detail: "IsolationForest scoring events..." },
  journey:  { label: "Journey Modeling",      detail: "LSTM training on action sequences..." },
  testgen:  { label: "Generating Test Cases", detail: "Extracting patterns from clusters, anomalies, journeys..." },
};

const STEP_DURATIONS = { ingest: 600, parse: 700, sanitize: 900, embed: 1800, cluster: 1000, anomaly: 900, journey: 1500, testgen: 700 };

const RESULT_TABS = {
  fraud:      [{ id: "findings",   label: "Fraud Findings", Icon: I.Shield,   count: r => r.fraud_findings.length },
               { id: "anomalies",  label: "Anomalies",      Icon: I.AlertTri, count: r => r.anomaly_summary.length },
               { id: "test_cases", label: "Test Cases",     Icon: I.TestTube, count: r => r.tests.length }],
  errors:     [{ id: "clusters",   label: "Error Clusters", Icon: I.Cluster,  count: r => r.cluster_summary.length },
               { id: "test_cases", label: "Test Cases",     Icon: I.TestTube, count: r => r.tests.length }],
  testgen:    [{ id: "test_cases", label: "Generated Tests", Icon: I.TestTube, count: r => r.tests.length }],
  journeys:   [{ id: "journeys",   label: "Journey Patterns", Icon: I.Route,   count: r => r.journey_insights.length },
               { id: "test_cases", label: "Test Cases",       Icon: I.TestTube, count: r => r.tests.length }],
  compliance: [{ id: "compliance", label: "Compliance",    Icon: I.Lock,     count: r => r.compliance_findings.length },
               { id: "test_cases", label: "Test Cases",    Icon: I.TestTube, count: r => r.tests.length }],
  full:       [{ id: "clusters",   label: "Clusters",      Icon: I.Cluster,  count: r => r.cluster_summary.length },
               { id: "anomalies",  label: "Anomalies",     Icon: I.AlertTri, count: r => r.anomaly_summary.length },
               { id: "findings",   label: "Fraud",         Icon: I.Shield,   count: r => r.fraud_findings.length },
               { id: "journeys",   label: "Journeys",      Icon: I.Route,    count: r => r.journey_insights.length },
               { id: "compliance", label: "Compliance",    Icon: I.Lock,     count: r => r.compliance_findings.length },
               { id: "test_cases", label: "Test Cases",    Icon: I.TestTube, count: r => r.tests.length }],
};

// ── File parsing (browser-side, lightweight) ───────────────────────────────
// Splits the raw text into an array of record objects so FastAPI can analyse them.
function parseFileContent(text, filename) {
  const ext = filename.split(".").pop().toLowerCase();
  if (ext === "jsonl" || ext === "ndjson") {
    return text.split("\n").map(l => l.trim()).filter(Boolean)
      .map(l => { try { return JSON.parse(l); } catch { return { message: l }; } });
  }
  if (ext === "json") {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed;
    const key = ["logs", "records", "events", "data"].find(k => Array.isArray(parsed[k]));
    return key ? parsed[key] : [parsed];
  }
  if (ext === "csv") {
    const lines = text.split("\n").filter(Boolean);
    const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
    return lines.slice(1).map(line => {
      const vals = line.split(",").map(v => v.trim().replace(/^"|"$/g, ""));
      return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
    });
  }
  return text.split("\n").filter(Boolean).map(l => ({ message: l }));
}

// ── API response → display shape (server already formats most fields) ──────
function normalizeResults(api) {
  return {
    cluster_summary:     api.clusters            || [],
    anomaly_summary:     api.anomalies           || [],
    fraud_findings:      api.fraud_findings      || [],
    compliance_findings: api.compliance_findings || [],
    journey_insights:    api.journeys            || [],
    tests:               api.tests               || [],
    summary:             api.summary             || {},
  };
}

// ── Sub-components ─────────────────────────────────────────────────────────
const SevBadge = ({ sev }) => <span className={`sev sev-${sev}`}>{sev}</span>;

const ClusterView = ({ data }) => (
  <div>
    <div className="sec-title">Error Clusters ({data.length} identified)</div>
    {data.length === 0
      ? <Empty icon={<I.Cluster />} msg="No clusters — try a larger log file (min 10 messages)." />
      : <div className="cl-grid">
          {data.map(c => (
            <div key={c.id} className="cl-card" style={{ borderLeftColor: c.color }}>
              <div className="cl-head"><span className="cl-name">{c.label}</span><SevBadge sev={c.severity} /></div>
              <div className="cl-count">{c.count.toLocaleString()} events</div>
              <div className="cl-sample">Top terms: {(c.top_terms || []).join(", ") || "—"}</div>
            </div>
          ))}
        </div>
    }
  </div>
);

const AnomalyView = ({ data }) => (
  <div>
    <div className="sec-title">Top Anomalies ({data.length} flagged)</div>
    {data.length === 0
      ? <Empty icon={<I.AlertTri />} msg="No anomalies — file needs ≥20 records for IsolationForest." />
      : <div className="an-list">
          {data.map(a => (
            <div key={a.id} className="an-row">
              <div className={`an-score ${a.score >= 0.8 ? "crit" : "warn"}`}>{a.score.toFixed(2)}</div>
              <div><div className="an-desc">{a.description}</div><div className="an-sess">{a.session}</div></div>
              <div className={`an-type an-type-${a.severity}`}>{a.severity}</div>
              <div className="an-time">{a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : "—"}</div>
            </div>
          ))}
        </div>
    }
  </div>
);

const FraudView = ({ findings, anomalies }) => (
  <div>
    <div className="sec-title">Fraud Findings ({findings.length} patterns)</div>
    {findings.length === 0
      ? <Empty icon={<I.Shield />} msg="No fraud patterns detected." />
      : <div className="fraud-list">
          {findings.map((f, i) => (
            <div key={i} className="fraud-card">
              <div className="fraud-head">
                <div className="fraud-cat-badge">{f.category.replace(/([A-Z])/g, " $1").trim()}</div>
                <SevBadge sev={f.severity} />
              </div>
              <div className="fraud-desc">{f.description}</div>
              {f.accounts?.length > 0 && (
                <div className="fraud-accounts">
                  {f.accounts.slice(0, 4).map(a => <span key={a} className="fraud-account">{a}</span>)}
                  {f.accounts.length > 4 && <span className="fraud-account-more">+{f.accounts.length - 4} more</span>}
                </div>
              )}
              {f.metrics && Object.keys(f.metrics).length > 0 && (
                <div className="fraud-metrics">
                  {Object.entries(f.metrics).map(([k, v]) => (
                    <span key={k} className="fraud-metric">{k}: <strong>{typeof v === "number" ? v.toLocaleString() : v}</strong></span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
    }
    {anomalies.length > 0 && (
      <><div className="sec-title" style={{ marginTop: 20 }}>Anomalous Sessions ({anomalies.length})</div><AnomalyView data={anomalies} /></>
    )}
  </div>
);

const ComplianceView = ({ findings }) => {
  const sevColor = { critical: "#EF4444", high: "#F97316", medium: "#FACC15", low: "#3B82F6" };
  return (
    <div>
      <div className="sec-title">Compliance Findings ({findings.length})</div>
      {findings.length === 0
        ? <Empty icon={<I.Lock />} msg="No compliance violations found." />
        : <div className="comp-list">
            {findings.map((f, i) => (
              <div key={i} className="comp-card" style={{ borderLeftColor: sevColor[f.severity] || "#545D68" }}>
                <div className="comp-head"><span className="comp-rule">{f.rule}</span><SevBadge sev={f.severity} /></div>
                <div className="comp-desc">{f.description}</div>
                {f.evidence?.length > 0 && (
                  <div className="comp-evidence">
                    <div className="comp-evidence-label">Evidence</div>
                    {f.evidence.map((e, j) => <div key={j} className="comp-evidence-item">— {e}</div>)}
                  </div>
                )}
              </div>
            ))}
          </div>
      }
    </div>
  );
};

const JourneyView = ({ data }) => (
  <div>
    <div className="sec-title">Journey Patterns ({data.length} sequences)</div>
    {data.length === 0
      ? <Empty icon={<I.Route />} msg="No journeys — LSTM requires ≥50 sequences to train." />
      : <div className="jr-list">
          {data.map(j => (
            <div key={j.id} className={`jr-row ${j.anomalous ? "anom" : ""}`}>
              <div className="jr-head">
                <span className="jr-label">{j.label}</span>
                <span className="jr-conf" style={{ color: j.anomalous ? "#EF4444" : "#10B981" }}>conf: {j.confidence.toFixed(3)}</span>
              </div>
              <div className="jr-path">
                {j.path.map((s, i) => (
                  <span key={i} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                    <span className="jr-step">{s}</span>
                    {i < j.path.length - 1 && <span className="jr-arrow"><I.Chevron /></span>}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
    }
  </div>
);

const GherkinView = ({ tests }) => {
  const [expanded, setExpanded] = useState({});
  return (
    <div>
      <div className="sec-title">Generated Test Scenarios ({tests.length})</div>
      {tests.length === 0
        ? <Empty icon={<I.TestTube />} msg="No test cases generated." />
        : <div className="tc-list">
            {tests.map((gherkin, i) => {
              const lines = gherkin.trim().split("\n");
              const title = lines[1]?.trim().replace(/^Scenario:\s*/, "") || `Scenario ${i + 1}`;
              const feature = lines[0]?.replace(/^Feature:\s*/, "") || "";
              return (
                <div key={i} className="tc-card">
                  <div className="tc-card-head" onClick={() => setExpanded(p => ({ ...p, [i]: !p[i] }))}>
                    <span className="tc-card-id" style={{ background: "rgba(16,185,129,0.12)", color: "#10B981" }}>
                      TC-{String(i + 1).padStart(3, "0")}
                    </span>
                    <span className="tc-card-title">{title}</span>
                    <span className="tc-card-pri" style={{ background: "rgba(59,130,246,0.1)", color: "#3B82F6" }}>{feature.slice(0, 28)}</span>
                    <span className={`tc-card-expand ${expanded[i] ? "open" : ""}`}><I.Chevron /></span>
                  </div>
                  {expanded[i] && (
                    <div className="tc-body">
                      <div className="gherkin-block">
                        {lines.map((line, j) => {
                          const kw = ["Feature:", "Scenario:", "Given", "When", "Then", "And", "But"].find(k => line.trim().startsWith(k));
                          return <div key={j} className={`gherkin-line gherkin-${kw ? kw.replace(":", "").toLowerCase() : "text"}`}>{line}</div>;
                        })}
                      </div>
                      <div className="tc-actions">
                        <button className="tc-action" onClick={() => navigator.clipboard.writeText(gherkin)}><I.Copy /> Copy</button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
      }
    </div>
  );
};

const Empty = ({ icon, msg }) => (
  <div className="empty-state">{icon}<span>{msg}</span></div>
);

const ExportBar = ({ info }) => (
  <div className="export-bar">
    <span className="export-info">{info}</span>
    <div className="export-btns">
      <button className="export-btn"><I.Download /> JSON</button>
      <button className="export-btn"><I.Download /> CSV</button>
    </div>
  </div>
);

// ── Source Panel: File upload + connector forms ────────────────────────────
const SOURCE_TABS = [
  { id: "file",      label: "Upload File",    Icon: I.Upload },
  { id: "elk",       label: "Elasticsearch",  Icon: I.Db     },
  { id: "datadog",   label: "Datadog",        Icon: I.Cloud  },
];

function SourcePanel({ onSourceReady, onSourceClear }) {
  const [srcTab, setSrcTab]     = useState("file");
  const [file, setFile]         = useState(null);       // { name, size, records }
  const [dragOver, setDragOver] = useState(false);
  const [elkCfg, setElkCfg]     = useState({ endpoint: "", index: "", api_key: "", username: "", password: "", verify_ssl: true });
  const [ddCfg, setDdCfg]       = useState({ api_key: "", app_key: "", query: "", region: "us", from: "now-1h", to: "now", limit: "500" });
  const fileInputRef            = useRef(null);

  const loadFile = (f) => {
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const records = parseFileContent(e.target.result, f.name);
        const loaded = { name: f.name, size: (f.size / 1024).toFixed(1) + " KB", records };
        setFile(loaded);
        onSourceReady({ records: loaded.records });
      } catch (err) {
        alert(`Failed to parse "${f.name}": ${err.message}`);
      }
    };
    reader.readAsText(f);
  };

  const clearFile = () => { setFile(null); onSourceClear(); };

  const applyElk = () => {
    if (!elkCfg.endpoint || !elkCfg.index) return alert("Endpoint and Index are required.");
    const auth = elkCfg.api_key
      ? { api_key: elkCfg.api_key }
      : elkCfg.username ? { username: elkCfg.username, password: elkCfg.password } : undefined;
    onSourceReady({ connectors: { elk: { endpoint: elkCfg.endpoint, index: elkCfg.index, ...(auth && { auth }), verify_ssl: elkCfg.verify_ssl } } });
  };

  const applyDatadog = () => {
    if (!ddCfg.api_key || !ddCfg.app_key || !ddCfg.query) return alert("API Key, App Key and Query are required.");
    onSourceReady({ connectors: { datadog: { api_key: ddCfg.api_key, app_key: ddCfg.app_key, query: ddCfg.query, region: ddCfg.region, timeframe: { from: ddCfg.from, to: ddCfg.to }, limit: parseInt(ddCfg.limit) || 500 } } });
  };

  const upd = (setter) => (key) => (e) => setter(prev => ({ ...prev, [key]: e.target.value }));

  return (
    <div className="source-panel">
      {/* Source type tabs */}
      <div className="src-tabs">
        {SOURCE_TABS.map(t => (
          <div key={t.id} className={`src-tab ${srcTab === t.id ? "active" : ""}`} onClick={() => { setSrcTab(t.id); onSourceClear(); clearFile(); }}>
            <t.Icon />{t.label}
          </div>
        ))}
      </div>

      {/* ── File upload ── */}
      {srcTab === "file" && (
        <div
          className={`upload ${dragOver ? "over" : ""}`}
          onClick={() => !file && fileInputRef.current?.click()}
          onDrop={e => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]); }}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
        >
          <input ref={fileInputRef} type="file" accept=".jsonl,.json,.csv,.log,.txt" style={{ display: "none" }} onChange={e => loadFile(e.target.files[0])} />
          {!file ? (
            <>
              <div style={{ color: "var(--t3)", display: "flex", justifyContent: "center", marginBottom: 4 }}><I.Upload /></div>
              <div className="upload-title">Drop log file here or click to browse</div>
              <div className="upload-sub">Browser reads the file · records sent to local Python server for analysis</div>
              <div className="upload-tags">{[".jsonl", ".csv", ".json", ".log"].map(f => <span key={f} className="upload-tag">{f}</span>)}</div>
            </>
          ) : (
            <div className="file-loaded">
              <I.File />
              <div><div className="name">{file.name}</div><div className="meta">{file.size} · {file.records.length.toLocaleString()} records parsed</div></div>
              <div className="ok"><I.Check /> Ready</div>
              <button className="clear-btn" onClick={e => { e.stopPropagation(); clearFile(); }}><I.X /></button>
            </div>
          )}
        </div>
      )}

      {/* ── Elasticsearch ── */}
      {srcTab === "elk" && (
        <div className="connector-form">
          <div className="conn-badge elk-badge">Elasticsearch / OpenSearch</div>
          <div className="form-row">
            <div className="form-field">
              <label>Endpoint *</label>
              <input placeholder="https://my-elk.internal:9200" value={elkCfg.endpoint} onChange={upd(setElkCfg)("endpoint")} />
            </div>
            <div className="form-field">
              <label>Index *</label>
              <input placeholder="logs-* or my-index" value={elkCfg.index} onChange={upd(setElkCfg)("index")} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-field">
              <label>API Key <span className="form-optional">(or use username/password)</span></label>
              <input type="password" placeholder="base64 encoded API key" value={elkCfg.api_key} onChange={upd(setElkCfg)("api_key")} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-field"><label>Username</label><input placeholder="elastic" value={elkCfg.username} onChange={upd(setElkCfg)("username")} /></div>
            <div className="form-field"><label>Password</label><input type="password" placeholder="••••••••" value={elkCfg.password} onChange={upd(setElkCfg)("password")} /></div>
          </div>
          <div className="form-check">
            <input type="checkbox" id="verify-ssl" checked={elkCfg.verify_ssl} onChange={e => setElkCfg(p => ({ ...p, verify_ssl: e.target.checked }))} />
            <label htmlFor="verify-ssl">Verify SSL certificate</label>
          </div>
          <button className="conn-apply" onClick={applyElk}><I.Check /> Connect to Elasticsearch</button>
        </div>
      )}

      {/* ── Datadog ── */}
      {srcTab === "datadog" && (
        <div className="connector-form">
          <div className="conn-badge dd-badge">Datadog Log Management</div>
          <div className="form-row">
            <div className="form-field"><label>API Key *</label><input type="password" placeholder="Datadog API key" value={ddCfg.api_key} onChange={upd(setDdCfg)("api_key")} /></div>
            <div className="form-field"><label>App Key *</label><input type="password" placeholder="Datadog application key" value={ddCfg.app_key} onChange={upd(setDdCfg)("app_key")} /></div>
          </div>
          <div className="form-row">
            <div className="form-field form-wide">
              <label>Log Query *</label>
              <input placeholder='service:payments status:error env:prod' value={ddCfg.query} onChange={upd(setDdCfg)("query")} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-field"><label>From</label><input placeholder="now-1h" value={ddCfg.from} onChange={upd(setDdCfg)("from")} /></div>
            <div className="form-field"><label>To</label><input placeholder="now" value={ddCfg.to} onChange={upd(setDdCfg)("to")} /></div>
            <div className="form-field"><label>Limit</label><input type="number" placeholder="500" value={ddCfg.limit} onChange={upd(setDdCfg)("limit")} /></div>
            <div className="form-field">
              <label>Region</label>
              <select value={ddCfg.region} onChange={upd(setDdCfg)("region")}>
                {["us", "us3", "us5", "eu", "ap1"].map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <button className="conn-apply" onClick={applyDatadog}><I.Check /> Connect to Datadog</button>
        </div>
      )}
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────
export default function LogMinerQA() {
  const [category, setCategory]             = useState("fraud");
  const [source, setSource]                 = useState(null);   // { records } or { connectors }
  const [sourceLabel, setSourceLabel]       = useState(null);   // display string for header
  const [running, setRunning]               = useState(false);
  const [done, setDone]                     = useState(false);
  const [error, setError]                   = useState(null);
  const [pct, setPct]                       = useState(0);
  const [activeStep, setActiveStep]         = useState(-1);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [results, setResults]               = useState(null);
  const [resultTab, setResultTab]           = useState(null);
  const animFrameRef                        = useRef(null);

  const catDef = CATEGORY_DEF[category];

  const selectCategory = (id) => {
    setCategory(id);
    setDone(false); setResults(null); setError(null);
    setRunning(false); setPct(0); setActiveStep(-1); setCompletedSteps([]);
  };

  const onSourceReady = (src) => {
    setSource(src);
    if (src.records)    setSourceLabel(`${src.records.length.toLocaleString()} records from file`);
    if (src.connectors) setSourceLabel(`Connected: ${Object.keys(src.connectors).join(", ")}`);
    setDone(false); setResults(null); setError(null);
  };

  const onSourceClear = () => { setSource(null); setSourceLabel(null); setDone(false); setResults(null); setError(null); };

  // ── Progress animation (runs while API call is in flight) ──────────────
  const animateProgress = (steps, onDone) => {
    const totalMs = steps.reduce((s, k) => s + (STEP_DURATIONS[k] || 700), 0);
    let stepStart = 0, si = 0;
    setActiveStep(0); setCompletedSteps([]);
    animFrameRef._startTs = null;

    const tick = (ts) => {
      if (!animFrameRef._startTs) animFrameRef._startTs = ts;
      const elapsed = ts - animFrameRef._startTs;
      setPct(Math.min((elapsed / totalMs) * 100, 95));
      const stepDur = STEP_DURATIONS[steps[si]] || 700;
      if (elapsed - stepStart > stepDur && si < steps.length - 1) {
        setCompletedSteps(prev => [...prev, steps[si]]);
        si++; stepStart = elapsed; setActiveStep(si);
      }
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      setCompletedSteps([...steps]); setActiveStep(-1); setPct(100);
      onDone();
    };
  };

  // ── Run analysis ───────────────────────────────────────────────────────
  const runAnalysis = useCallback(async () => {
    if (!source || running) return;
    setRunning(true); setDone(false); setError(null); setResults(null);
    setCompletedSteps([]); setPct(0);

    const steps = catDef.pipelineKeys;
    let finishAnimation;
    const animDone = new Promise(resolve => { finishAnimation = animateProgress(steps, resolve); });

    try {
      const resp = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(source),   // { records } or { connectors }
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Server ${resp.status}: ${text.slice(0, 200)}`);
      }
      const data = await resp.json();
      finishAnimation(); await animDone;
      setResults(normalizeResults(data));
      setResultTab(RESULT_TABS[category][0].id);
      setDone(true);
    } catch (err) {
      finishAnimation(); await animDone;
      const isNet = err.message.includes("fetch") || err.message.includes("Failed to fetch");
      setError(isNet
        ? `Cannot reach backend at ${API_BASE}.\n\nStart it:\n  cd c:\\Users\\abirm\\LogMiner-QA\n  .venv\\Scripts\\python -m uvicorn logminer_qa.server:create_app --factory --port 8080 --app-dir src`
        : err.message);
    } finally {
      setRunning(false);
    }
  }, [source, running, category, catDef]);

  const tabs = results ? (RESULT_TABS[category] || []) : [];

  const renderResults = () => {
    if (!results) return null;
    switch (resultTab) {
      case "clusters":   return <ClusterView data={results.cluster_summary} />;
      case "anomalies":  return <AnomalyView data={results.anomaly_summary} />;
      case "findings":   return <FraudView findings={results.fraud_findings} anomalies={results.anomaly_summary} />;
      case "journeys":   return <JourneyView data={results.journey_insights} />;
      case "compliance": return <ComplianceView findings={results.compliance_findings} />;
      case "test_cases": return <GherkinView tests={results.tests} />;
      default: return null;
    }
  };

  const exportLabel = { clusters: "clusters", anomalies: "anomalies", findings: "fraud patterns", journeys: "journey patterns", compliance: "compliance findings", test_cases: "test scenarios" };

  return (
    <div className="app">
      <style>{CSS}</style>

      {/* Header */}
      <div className="hdr">
        <div className="hdr-logo"><span>LogMiner</span>-QA</div>
        <div className="hdr-sep" />
        <div className="hdr-nav">
          {["Analyze", "History", "Settings"].map((t, i) => (
            <div key={t} className={`hdr-tab ${i === 0 ? "active" : ""}`}>{t}</div>
          ))}
        </div>
        <div className="hdr-right">
          <div className="hdr-dot" style={{ background: source ? "var(--green)" : "var(--t3)" }} />
          <div className="hdr-status">{sourceLabel || "No source connected"}</div>
        </div>
      </div>

      <div className="body">
        {/* Sidebar */}
        <div className="sidebar">
          <div className="sidebar-label">Analysis Mode</div>
          {Object.values(CATEGORY_DEF).map(cat => (
            <div key={cat.id} className={`cat-item ${category === cat.id ? "active" : ""}`} onClick={() => selectCategory(cat.id)}>
              <div className="cat-icon" style={{ background: cat.bgColor, color: cat.color }}><cat.Icon /></div>
              <div className="cat-text">
                <div className="cat-name" style={{ color: category === cat.id ? cat.color : "var(--t1)" }}>{cat.label}</div>
                <div className="cat-desc">{cat.desc}</div>
              </div>
              <div className="cat-active-bar" style={{ background: cat.color }} />
            </div>
          ))}
        </div>

        {/* Main panel */}
        <div className="main">

          {/* Source selection */}
          <SourcePanel onSourceReady={onSourceReady} onSourceClear={onSourceClear} />

          {/* Analysis config */}
          <div className="cfg">
            {Object.entries(catDef.configOptions).map(([key, opt]) => (
              <div key={key} className="cfg-card">
                <div className="cfg-label">{opt.label}</div>
                <select className="sel">{opt.opts.map(o => <option key={o}>{o}</option>)}</select>
              </div>
            ))}
          </div>

          {/* Run button */}
          <button
            className="run"
            style={{ background: `linear-gradient(135deg, ${catDef.color}, ${catDef.color}bb)`, boxShadow: running ? "none" : `0 4px 20px ${catDef.color}44` }}
            onClick={runAnalysis}
            disabled={!source || running}
          >
            {running ? <I.Zap /> : <I.Play />}
            {running ? `Running ${catDef.label}...` : `Run ${catDef.label}`}
          </button>

          {/* Error */}
          {error && (
            <div className="error-box">
              <div className="error-title"><I.AlertTri /> Analysis Failed</div>
              <pre className="error-msg">{error}</pre>
            </div>
          )}

          {/* Pipeline progress */}
          {(running || done) && !error && (
            <div className="pipe">
              <div className="pipe-header">
                <span className="pipe-title" style={{ color: done ? "var(--green)" : catDef.color }}>
                  {done ? `✓ ${catDef.label} complete` : PIPELINE_META[catDef.pipelineKeys[activeStep]]?.label || "Initializing..."}
                </span>
                <span className="pipe-pct">{Math.round(pct)}%</span>
              </div>
              <div className="pipe-track">
                <div className="pipe-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${catDef.color}, ${catDef.color}88)` }} />
              </div>
              <div className="pipe-steps">
                {catDef.pipelineKeys.map(key => {
                  const isDone = completedSteps.includes(key);
                  const isActive = catDef.pipelineKeys[activeStep] === key && running;
                  return (
                    <div key={key} className={`pipe-step ${isDone ? "done" : isActive ? "active" : ""}`}>
                      <div className="pipe-dot" />
                      <div className="pipe-info">
                        <div className="label">{PIPELINE_META[key]?.label}</div>
                        {(isActive || isDone) && <div className="detail">{PIPELINE_META[key]?.detail}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Results */}
          {done && results && (
            <>
              <div className="tabs">
                {tabs.map(t => (
                  <div key={t.id} className={`tab ${resultTab === t.id ? "active" : ""}`} onClick={() => setResultTab(t.id)}>
                    <t.Icon />{t.label}<span className="tab-badge">{t.count(results)}</span>
                  </div>
                ))}
              </div>
              <div className="results">
                {renderResults()}
                {resultTab && <ExportBar info={`${results[{ clusters: "cluster_summary", anomalies: "anomaly_summary", findings: "fraud_findings", journeys: "journey_insights", compliance: "compliance_findings", test_cases: "tests" }[resultTab]]?.length || 0} ${exportLabel[resultTab]}`} />}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');
:root {
  --bg0:#080B11;--bg1:#0D1117;--bg2:#131922;--bg3:#1A2130;
  --bd:#1C2435;--bd2:#2A3548;
  --t1:#E6EDF3;--t2:#8B949E;--t3:#545D68;
  --orange:#F97316;--red:#EF4444;--green:#10B981;--blue:#3B82F6;--purple:#A855F7;--cyan:#06B6D4;--yellow:#FACC15;
  --mono:'JetBrains Mono',monospace;--sans:'Outfit',sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box;}
.app{font-family:var(--sans);background:var(--bg0);color:var(--t1);min-height:100vh;display:flex;flex-direction:column;}
.hdr{height:48px;background:var(--bg1);border-bottom:1px solid var(--bd);display:flex;align-items:center;padding:0 20px;position:sticky;top:0;z-index:50;flex-shrink:0;}
.hdr-logo{font-family:var(--mono);font-weight:700;font-size:15px;letter-spacing:-0.5px;}
.hdr-logo span{color:var(--orange);}
.hdr-sep{width:1px;height:20px;background:var(--bd);margin:0 16px;}
.hdr-nav{display:flex;gap:2px;}
.hdr-tab{padding:6px 14px;font-size:13px;font-weight:500;color:var(--t3);cursor:pointer;border-radius:6px;transition:all .15s;}
.hdr-tab:hover{color:var(--t2);background:var(--bg2);}
.hdr-tab.active{color:var(--orange);background:var(--bg2);}
.hdr-right{margin-left:auto;display:flex;align-items:center;gap:10px;}
.hdr-dot{width:7px;height:7px;border-radius:50%;transition:background .3s;}
.hdr-status{font-family:var(--mono);font-size:10px;color:var(--t3);}
.body{display:flex;flex:1;overflow:hidden;}
.sidebar{width:220px;flex-shrink:0;background:var(--bg1);border-right:1px solid var(--bd);padding:16px 12px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;}
.sidebar-label{font-family:var(--mono);font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--t3);padding:0 8px;margin-bottom:4px;}
.cat-item{display:flex;align-items:flex-start;gap:10px;padding:10px;border-radius:8px;cursor:pointer;transition:all .15s;border:1px solid transparent;}
.cat-item:hover{background:var(--bg2);}
.cat-item.active{border-color:var(--bd2);background:var(--bg2);}
.cat-icon{width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;}
.cat-text{flex:1;min-width:0;}
.cat-name{font-size:12px;font-weight:600;line-height:1.2;}
.cat-desc{font-size:10px;color:var(--t3);margin-top:2px;line-height:1.3;}
.cat-active-bar{width:3px;border-radius:2px;align-self:stretch;flex-shrink:0;opacity:0;}
.cat-item.active .cat-active-bar{opacity:1;}
.main{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:0;}

/* Source panel */
.source-panel{background:var(--bg1);border:1px solid var(--bd);border-radius:10px;margin-bottom:16px;overflow:hidden;}
.src-tabs{display:flex;border-bottom:1px solid var(--bd);}
.src-tab{display:flex;align-items:center;gap:6px;padding:10px 16px;font-size:12px;font-weight:500;color:var(--t3);cursor:pointer;transition:all .15s;border-bottom:2px solid transparent;margin-bottom:-1px;}
.src-tab:hover{color:var(--t2);}
.src-tab.active{color:var(--orange);border-bottom-color:var(--orange);}

/* Upload zone */
.upload{padding:24px;text-align:center;cursor:pointer;transition:all .2s;background:transparent;}
.upload:hover,.upload.over{background:rgba(249,115,22,.03);}
.upload-title{font-weight:600;font-size:14px;margin:8px 0 2px;}
.upload-sub{font-size:12px;color:var(--t3);}
.upload-tags{display:flex;gap:6px;justify-content:center;margin-top:10px;}
.upload-tag{font-family:var(--mono);font-size:9px;padding:2px 7px;border-radius:3px;background:var(--bg2);color:var(--t3);border:1px solid var(--bd);}
.file-loaded{display:flex;align-items:center;gap:10px;justify-content:center;}
.file-loaded .name{font-weight:600;font-size:13px;}
.file-loaded .meta{font-family:var(--mono);font-size:11px;color:var(--t3);}
.file-loaded .ok{display:flex;align-items:center;gap:4px;color:var(--green);font-family:var(--mono);font-size:11px;margin-left:8px;}
.clear-btn{display:flex;align-items:center;padding:4px;background:transparent;border:1px solid var(--bd);border-radius:4px;color:var(--t3);cursor:pointer;margin-left:6px;transition:all .15s;}
.clear-btn:hover{border-color:var(--red);color:var(--red);}

/* Connector forms */
.connector-form{padding:16px 20px 20px;}
.conn-badge{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 10px;border-radius:4px;display:inline-block;margin-bottom:14px;}
.elk-badge{background:rgba(59,130,246,0.12);color:var(--blue);}
.dd-badge{background:rgba(168,85,247,0.12);color:var(--purple);}
.form-row{display:flex;gap:12px;margin-bottom:10px;}
.form-field{display:flex;flex-direction:column;gap:4px;flex:1;}
.form-field.form-wide{flex:2;}
.form-field label{font-family:var(--mono);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--t3);}
.form-optional{text-transform:none;letter-spacing:0;font-weight:400;color:var(--t3);opacity:.7;}
.form-field input,.form-field select{background:var(--bg2);border:1px solid var(--bd);border-radius:5px;color:var(--t1);font-family:var(--mono);font-size:11px;padding:7px 10px;outline:none;width:100%;}
.form-field input:focus,.form-field select:focus{border-color:var(--orange);}
.form-field input::placeholder{color:var(--t3);}
.form-check{display:flex;align-items:center;gap:8px;margin-bottom:14px;font-size:12px;color:var(--t2);}
.form-check input{width:auto;accent-color:var(--orange);}
.conn-apply{display:flex;align-items:center;gap:6px;padding:8px 16px;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;color:var(--t1);font-family:var(--mono);font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;}
.conn-apply:hover{border-color:var(--orange);color:var(--orange);}

.cfg{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px;}
.cfg-card{background:var(--bg1);border:1px solid var(--bd);border-radius:8px;padding:10px 12px;}
.cfg-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--t3);font-family:var(--mono);margin-bottom:5px;}
.sel{width:100%;background:var(--bg2);border:1px solid var(--bd);border-radius:5px;color:var(--t1);font-family:var(--sans);font-size:12px;padding:7px 10px;outline:none;cursor:pointer;appearance:none;}
.sel:focus{border-color:var(--orange);}
.run{display:flex;align-items:center;gap:8px;color:#fff;border:none;border-radius:7px;padding:10px 24px;font-family:var(--mono);font-weight:600;font-size:12px;cursor:pointer;transition:all .2s;letter-spacing:.3px;margin-bottom:16px;}
.run:hover:not(:disabled){transform:translateY(-1px);}
.run:disabled{opacity:.5;cursor:not-allowed;}
.error-box{background:#ef444410;border:1px solid #ef444430;border-radius:8px;padding:14px 16px;margin-bottom:16px;}
.error-title{display:flex;align-items:center;gap:6px;color:var(--red);font-weight:600;font-size:13px;margin-bottom:8px;}
.error-msg{font-family:var(--mono);font-size:11px;color:var(--t2);white-space:pre-wrap;line-height:1.6;}
.pipe{background:var(--bg1);border:1px solid var(--bd);border-radius:10px;padding:14px 18px;margin-bottom:16px;}
.pipe-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.pipe-title{font-family:var(--mono);font-size:12px;font-weight:600;}
.pipe-pct{font-family:var(--mono);font-size:12px;color:var(--t3);}
.pipe-track{width:100%;height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;margin-bottom:12px;}
.pipe-fill{height:100%;border-radius:2px;transition:width .4s linear;}
.pipe-steps{display:flex;flex-direction:column;gap:4px;}
.pipe-step{display:flex;align-items:flex-start;gap:10px;font-size:11px;font-family:var(--mono);color:var(--t3);padding:5px 6px;border-radius:5px;transition:all .2s;}
.pipe-step.active{background:rgba(249,115,22,.06);color:var(--orange);}
.pipe-step.done{color:var(--green);}
.pipe-dot{width:8px;height:8px;border-radius:50%;background:var(--bd);flex-shrink:0;margin-top:2px;transition:all .2s;}
.pipe-step.done .pipe-dot{background:var(--green);}
.pipe-step.active .pipe-dot{background:var(--orange);box-shadow:0 0 8px #f9731688;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.4;}}
.pipe-info .label{font-weight:600;}
.pipe-info .detail{font-size:10px;color:var(--t3);margin-top:1px;}
.tabs{display:flex;gap:2px;background:var(--bg1);border:1px solid var(--bd);border-radius:8px 8px 0 0;padding:3px;overflow-x:auto;}
.tab{display:flex;align-items:center;gap:5px;padding:7px 12px;font-size:12px;font-weight:500;color:var(--t3);cursor:pointer;border-radius:5px;transition:all .15s;white-space:nowrap;}
.tab:hover{color:var(--t2);background:var(--bg3);}
.tab.active{color:var(--orange);background:var(--bg2);}
.tab-badge{font-family:var(--mono);font-size:9px;padding:1px 5px;border-radius:8px;background:var(--bg3);color:var(--t3);}
.tab.active .tab-badge{background:rgba(249,115,22,.12);color:var(--orange);}
.results{background:var(--bg1);border:1px solid var(--bd);border-top:none;border-radius:0 0 8px 8px;padding:16px;min-height:300px;}
.sec-title{font-size:11px;font-family:var(--mono);font-weight:600;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;margin-bottom:14px;display:flex;align-items:center;gap:8px;}
.sec-title::after{content:'';flex:1;height:1px;background:var(--bd);}
.sev{font-family:var(--mono);font-size:9px;font-weight:600;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.3px;}
.sev-critical,.sev-high{background:#ef444420;color:var(--red);}
.sev-medium{background:#f9731620;color:var(--orange);}
.sev-low{background:#3b82f620;color:var(--blue);}
.sev-none{background:#10b98120;color:var(--green);}
.cl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;}
.cl-card{background:var(--bg2);border:1px solid var(--bd);border-radius:7px;padding:12px;border-left:3px solid;}
.cl-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;}
.cl-name{font-weight:600;font-size:12px;}
.cl-count{font-family:var(--mono);font-size:11px;color:var(--t3);}
.cl-sample{font-family:var(--mono);font-size:10px;color:var(--t3);background:var(--bg0);padding:6px 8px;border-radius:4px;margin-top:6px;word-break:break-all;}
.an-list{display:flex;flex-direction:column;gap:6px;}
.an-row{display:grid;grid-template-columns:56px 1fr 72px 60px;gap:12px;align-items:center;background:var(--bg2);border:1px solid var(--bd);border-radius:7px;padding:10px 12px;}
.an-score{font-family:var(--mono);font-weight:700;font-size:16px;}
.an-score.crit{color:var(--red);}.an-score.warn{color:var(--orange);}
.an-desc{font-size:12px;line-height:1.3;word-break:break-word;}
.an-sess{font-family:var(--mono);font-size:10px;color:var(--t3);}
.an-type{font-family:var(--mono);font-size:9px;font-weight:600;padding:2px 7px;border-radius:3px;text-transform:uppercase;text-align:center;}
.an-type-high{background:#ef444418;color:var(--red);}
.an-type-medium,.an-type-anomaly{background:#a855f718;color:var(--purple);}
.an-time{font-family:var(--mono);font-size:10px;color:var(--t3);text-align:right;}
.fraud-list{display:flex;flex-direction:column;gap:8px;}
.fraud-card{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:14px;}
.fraud-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;}
.fraud-cat-badge{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--red);background:#ef444412;padding:2px 8px;border-radius:4px;}
.fraud-desc{font-size:12px;color:var(--t2);margin-bottom:8px;}
.fraud-accounts{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;}
.fraud-account{font-family:var(--mono);font-size:10px;padding:2px 8px;background:var(--bg0);border:1px solid var(--bd);border-radius:3px;color:var(--t3);}
.fraud-account-more{font-family:var(--mono);font-size:10px;color:var(--t3);}
.fraud-metrics{display:flex;gap:12px;flex-wrap:wrap;}
.fraud-metric{font-family:var(--mono);font-size:10px;color:var(--t3);}
.fraud-metric strong{color:var(--t2);}
.comp-list{display:flex;flex-direction:column;gap:10px;}
.comp-card{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:14px;border-left:3px solid;}
.comp-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;}
.comp-rule{font-family:var(--mono);font-size:12px;font-weight:700;}
.comp-desc{font-size:12px;color:var(--t2);margin-bottom:8px;}
.comp-evidence{background:var(--bg0);border-radius:4px;padding:8px 10px;}
.comp-evidence-label{font-family:var(--mono);font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--t3);margin-bottom:4px;}
.comp-evidence-item{font-family:var(--mono);font-size:10px;color:var(--t3);line-height:1.6;}
.jr-list{display:flex;flex-direction:column;gap:10px;}
.jr-row{background:var(--bg2);border:1px solid var(--bd);border-radius:7px;padding:12px;border-left:3px solid var(--green);}
.jr-row.anom{border-left-color:var(--red);}
.jr-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}
.jr-label{font-weight:600;font-size:12px;}
.jr-conf{font-family:var(--mono);font-size:11px;font-weight:600;}
.jr-path{display:flex;align-items:center;gap:3px;flex-wrap:wrap;}
.jr-step{font-family:var(--mono);font-size:10px;padding:3px 8px;border-radius:3px;background:var(--bg0);color:var(--t2);border:1px solid var(--bd);}
.jr-arrow{color:var(--t3);}
.tc-list{display:flex;flex-direction:column;gap:6px;}
.tc-card{background:var(--bg2);border:1px solid var(--bd);border-radius:7px;overflow:hidden;}
.tc-card-head{display:flex;align-items:center;gap:10px;padding:10px 12px;cursor:pointer;}
.tc-card-id{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;white-space:nowrap;}
.tc-card-title{font-size:12px;font-weight:500;flex:1;}
.tc-card-pri{font-family:var(--mono);font-size:9px;padding:2px 8px;border-radius:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;}
.tc-card-expand{color:var(--t3);transition:transform .2s;flex-shrink:0;}
.tc-card-expand.open{transform:rotate(90deg);}
.tc-body{padding:0 12px 12px;border-top:1px solid var(--bd);}
.gherkin-block{background:var(--bg0);border-radius:6px;padding:12px;margin-top:10px;font-family:var(--mono);font-size:11px;line-height:1.8;}
.gherkin-feature{color:var(--blue);font-weight:700;}
.gherkin-scenario{color:var(--purple);font-weight:700;}
.gherkin-given{color:var(--cyan);}
.gherkin-when{color:var(--orange);}
.gherkin-then{color:var(--green);}
.gherkin-and,.gherkin-but{color:var(--t2);}
.gherkin-text{color:var(--t3);}
.tc-actions{display:flex;gap:6px;margin-top:10px;}
.tc-action{display:flex;align-items:center;gap:4px;padding:4px 10px;background:var(--bg3);border:1px solid var(--bd);border-radius:5px;color:var(--t2);font-family:var(--mono);font-size:10px;cursor:pointer;transition:all .15s;}
.tc-action:hover{border-color:var(--orange);color:var(--orange);}
.export-bar{display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding:9px 12px;background:var(--bg2);border:1px solid var(--bd);border-radius:7px;}
.export-info{font-size:11px;color:var(--t3);font-family:var(--mono);}
.export-btns{display:flex;gap:6px;}
.export-btn{display:flex;align-items:center;gap:4px;padding:4px 10px;background:var(--bg1);border:1px solid var(--bd);border-radius:5px;color:var(--t2);font-family:var(--mono);font-size:10px;cursor:pointer;transition:all .15s;}
.export-btn:hover{border-color:var(--orange);color:var(--orange);}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;min-height:180px;color:var(--t3);font-size:13px;}
.app ::-webkit-scrollbar{width:5px;}
.app ::-webkit-scrollbar-track{background:transparent;}
.app ::-webkit-scrollbar-thumb{background:var(--bd);border-radius:3px;}
`;
