import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000";

// ── Utility ──────────────────────────────────────────────────────────────────
const cn = (...classes) => classes.filter(Boolean).join(" ");

// ── Icons (inline SVG) ────────────────────────────────────────────────────────
const Icon = {
  Copy: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
    </svg>
  ),
  Check: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  Key: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>
    </svg>
  ),
  Link: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  ),
  Eye: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  Edit: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  ),
  Send: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  ),
  X: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  ArrowLeft: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
    </svg>
  ),
};

// ── Small reusable components ─────────────────────────────────────────────────
function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(text); } catch { }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className={cn("copy-btn", copied && "copied")}>
      {copied ? <Icon.Check /> : <Icon.Copy />}
      <span>{copied ? "Copied!" : label}</span>
    </button>
  );
}

function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className={cn("toast", `toast-${type}`)}>
      <span>{message}</span>
      <button onClick={onClose}><Icon.X /></button>
    </div>
  );
}

function Spinner() {
  return <div className="spinner" />;
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: "share",  label: "Share Text",   Icon: Icon.Send },
  { id: "view",   label: "View",          Icon: Icon.Eye  },
  { id: "edit",   label: "Edit",          Icon: Icon.Edit },
];

// ── Share Tab ─────────────────────────────────────────────────────────────────
function ShareTab({ onToast }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/text/store`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("Failed to share text");
      const data = await res.json();
      setResult(data);
      onToast("Text shared successfully!", "success");
    } catch (e) {
      onToast(e.message || "Something went wrong", "error");
    } finally {
      setLoading(false);
    }
  };

  const shareUrl = result ? `${window.location.origin}?id=${result.text_id}` : "";

  if (result) return (
    <div className="result-card">
      <div className="result-header">
        <div className="result-badge">✦ Shared</div>
        <button className="ghost-btn" onClick={() => { setResult(null); setText(""); }}>
          <Icon.ArrowLeft /> New
        </button>
      </div>

      <div className="info-block">
        <label><Icon.Link /> Share Link</label>
        <div className="copy-row">
          <span className="mono truncate">{shareUrl}</span>
          <CopyButton text={shareUrl} />
        </div>
      </div>

      <div className="info-block">
        <label><Icon.Key /> Secret Key <em>(keep this private!)</em></label>
        <div className="copy-row secret">
          <span className="mono truncate">{result.secret_key}</span>
          <CopyButton text={result.secret_key} label="Copy key" />
        </div>
        <p className="hint">You'll need this key to edit your text later.</p>
      </div>

      <div className="info-block">
        <label>Text ID</label>
        <div className="copy-row">
          <span className="mono small truncate">{result.text_id}</span>
          <CopyButton text={result.text_id} label="Copy ID" />
        </div>
      </div>
    </div>
  );

  return (
    <div className="tab-content">
      <p className="tab-desc">Paste or type your text below. You'll get a shareable link and a secret key to edit it later.</p>
      <div className="textarea-wrap">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Start typing your text here…"
          rows={10}
        />
        <div className="char-count">{text.length} chars</div>
      </div>
      <button
        className="primary-btn"
        onClick={handleSubmit}
        disabled={loading || !text.trim()}
      >
        {loading ? <Spinner /> : <><Icon.Send /> Generate Link</>}
      </button>
    </div>
  );
}

// ── View Tab ──────────────────────────────────────────────────────────────────
function ViewTab({ onToast }) {
  const [id, setId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Auto-fill from URL param
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get("id");
    if (urlId) { setId(urlId); }
  }, []);

  const handleFetch = async () => {
    if (!id.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/text/${id.trim()}`);
      if (!res.ok) throw new Error("Text not found or has been deleted");
      const data = await res.json();
      setResult(data);
    } catch (e) {
      onToast(e.message || "Something went wrong", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-content">
      <p className="tab-desc">Enter a Text ID to view shared content.</p>
      <div className="input-row">
        <input
          type="text"
          value={id}
          onChange={e => setId(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleFetch()}
          placeholder="Paste Text ID here…"
          className="mono"
        />
        <button className="primary-btn sm" onClick={handleFetch} disabled={loading || !id.trim()}>
          {loading ? <Spinner /> : <><Icon.Eye /> View</>}
        </button>
      </div>

      {result && (
        <div className="view-result">
          <div className="view-meta">
            <span>ID: <em className="mono">{id}</em></span>
            <CopyButton text={result.result} label="Copy text" />
          </div>
          <div className="view-text">{result.result}</div>
        </div>
      )}
    </div>
  );
}

// ── Edit Tab ──────────────────────────────────────────────────────────────────
function EditTab({ onToast }) {
  const [secretKey, setSecretKey] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetched, setFetched] = useState(false);

  const handleFetch = async () => {
    if (!secretKey.trim()) return;
    setFetching(true);
    setFetched(false);
    try {
      const res = await fetch(`${API_BASE}/text?secret_key=${secretKey.trim()}`);
      if (!res.ok) throw new Error("Invalid secret key");
      const data = await res.json();
      setText(data.text);
      setFetched(true);
    } catch (e) {
      onToast(e.message || "Something went wrong", "error");
    } finally {
      setFetching(false);
    }
  };

  const handleUpdate = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/text/get`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, secret_key: secretKey }),
      });
      if (!res.ok) throw new Error("Failed to update — check your secret key");
      onToast("Text updated successfully!", "success");
    } catch (e) {
      onToast(e.message || "Something went wrong", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-content">
      <p className="tab-desc">Paste your secret key to load and edit your shared text.</p>

      <div className="field">
        <label><Icon.Key /> Secret Key</label>
        <input
          type="password"
          value={secretKey}
          onChange={e => setSecretKey(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !fetched && handleFetch()}
          placeholder="Paste your secret key…"
          className="mono"
          disabled={fetched}
        />
      </div>

      {!fetched ? (
        <button
          className="secondary-btn"
          onClick={handleFetch}
          disabled={fetching || !secretKey.trim()}
        >
          {fetching ? <Spinner /> : <><Icon.Eye /> Load Text</>}
        </button>
      ) : (
        <>
          <div className="textarea-wrap">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Edit your text…"
              rows={10}
            />
            <div className="char-count">{text.length} chars</div>
          </div>
          <div className="btn-row">
            <button className="ghost-btn" onClick={() => { setFetched(false); setText(""); }}>Cancel</button>
            <button
              className="primary-btn"
              onClick={handleUpdate}
              disabled={loading || !text.trim()}
            >
              {loading ? <Spinner /> : <><Icon.Edit /> Update Text</>}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("share");
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "success") => {
    const id = Date.now();
    setToasts(p => [...p, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(p => p.filter(t => t.id !== id));
  }, []);

  // Auto-switch to View tab if URL has ?id=
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("id")) setTab("view");
  }, []);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
          --bg:       #0c0c0f;
          --surface:  #14141a;
          --border:   #22222e;
          --border2:  #2e2e3e;
          --text:     #e8e8f0;
          --muted:    #6b6b80;
          --accent:   #7c6aff;
          --accent2:  #ff6a9b;
          --success:  #4ade80;
          --error:    #f87171;
          --radius:   12px;
          --radius-lg:18px;
        }

        body {
          font-family: 'DM Sans', sans-serif;
          background: var(--bg);
          color: var(--text);
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 2rem 1rem 4rem;
        }

        /* ── Header ── */
        .header {
          text-align: center;
          margin-bottom: 2.5rem;
        }
        .wordmark {
          font-family: 'Syne', sans-serif;
          font-weight: 800;
          font-size: clamp(2rem, 5vw, 3rem);
          letter-spacing: -0.03em;
          background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .tagline {
          color: var(--muted);
          font-size: 0.9rem;
          margin-top: 0.4rem;
          font-weight: 300;
        }

        /* ── Card ── */
        .card {
          width: 100%;
          max-width: 640px;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        /* ── Tabs ── */
        .tabs {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          border-bottom: 1px solid var(--border);
        }
        .tab-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.4rem;
          padding: 0.85rem 0.5rem;
          background: none;
          border: none;
          color: var(--muted);
          font-family: 'Syne', sans-serif;
          font-size: 0.8rem;
          font-weight: 600;
          letter-spacing: 0.03em;
          cursor: pointer;
          transition: color 0.2s, background 0.2s;
          position: relative;
        }
        .tab-btn:hover { color: var(--text); background: rgba(255,255,255,0.03); }
        .tab-btn.active { color: var(--accent); }
        .tab-btn.active::after {
          content: '';
          position: absolute;
          bottom: -1px;
          left: 0; right: 0;
          height: 2px;
          background: linear-gradient(90deg, var(--accent), var(--accent2));
        }
        .tab-icon { display: flex; align-items: center; }

        /* ── Tab content ── */
        .tab-content {
          padding: 1.75rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .tab-desc {
          color: var(--muted);
          font-size: 0.875rem;
          line-height: 1.6;
        }

        /* ── Textarea ── */
        .textarea-wrap { position: relative; }
        textarea {
          width: 100%;
          background: var(--bg);
          border: 1px solid var(--border2);
          border-radius: var(--radius);
          color: var(--text);
          font-family: 'DM Sans', sans-serif;
          font-size: 0.9rem;
          line-height: 1.7;
          padding: 1rem;
          resize: vertical;
          transition: border-color 0.2s;
          outline: none;
        }
        textarea:focus { border-color: var(--accent); }
        .char-count {
          position: absolute;
          bottom: 0.6rem;
          right: 0.75rem;
          font-size: 0.72rem;
          color: var(--muted);
          pointer-events: none;
        }

        /* ── Inputs ── */
        .field { display: flex; flex-direction: column; gap: 0.5rem; }
        .field label {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.8rem;
          font-weight: 500;
          color: var(--muted);
          font-family: 'Syne', sans-serif;
          letter-spacing: 0.04em;
        }
        input[type="text"], input[type="password"] {
          width: 100%;
          background: var(--bg);
          border: 1px solid var(--border2);
          border-radius: var(--radius);
          color: var(--text);
          font-family: 'DM Sans', sans-serif;
          font-size: 0.9rem;
          padding: 0.75rem 1rem;
          outline: none;
          transition: border-color 0.2s;
        }
        input[type="text"]:focus, input[type="password"]:focus { border-color: var(--accent); }
        input.mono, textarea.mono { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }

        .input-row {
          display: flex;
          gap: 0.75rem;
          align-items: center;
        }
        .input-row input { flex: 1; }

        /* ── Buttons ── */
        .primary-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          background: linear-gradient(135deg, var(--accent), var(--accent2));
          color: #fff;
          border: none;
          border-radius: var(--radius);
          font-family: 'Syne', sans-serif;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.2s, transform 0.15s;
          letter-spacing: 0.02em;
          align-self: flex-start;
        }
        .primary-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
        .primary-btn:disabled { opacity: 0.45; cursor: not-allowed; }
        .primary-btn.sm { padding: 0.65rem 1rem; white-space: nowrap; }

        .secondary-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.7rem 1.25rem;
          background: transparent;
          color: var(--accent);
          border: 1px solid var(--accent);
          border-radius: var(--radius);
          font-family: 'Syne', sans-serif;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s;
          align-self: flex-start;
        }
        .secondary-btn:hover:not(:disabled) { background: rgba(124,106,255,0.1); }
        .secondary-btn:disabled { opacity: 0.45; cursor: not-allowed; }

        .ghost-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.55rem 0.9rem;
          background: transparent;
          border: 1px solid var(--border2);
          border-radius: var(--radius);
          color: var(--muted);
          font-size: 0.8rem;
          font-family: 'Syne', sans-serif;
          font-weight: 600;
          cursor: pointer;
          transition: color 0.2s, border-color 0.2s;
        }
        .ghost-btn:hover { color: var(--text); border-color: var(--border2); }

        .btn-row { display: flex; gap: 0.75rem; align-items: center; }

        .copy-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.4rem 0.75rem;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border2);
          border-radius: 8px;
          color: var(--muted);
          font-size: 0.75rem;
          font-family: 'Syne', sans-serif;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .copy-btn:hover { color: var(--text); border-color: var(--accent); }
        .copy-btn.copied { color: var(--success); border-color: var(--success); }

        /* ── Result card ── */
        .result-card {
          padding: 1.75rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .result-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .result-badge {
          font-family: 'Syne', sans-serif;
          font-size: 0.8rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          color: var(--success);
          background: rgba(74,222,128,0.1);
          border: 1px solid rgba(74,222,128,0.25);
          padding: 0.3rem 0.75rem;
          border-radius: 99px;
        }

        .info-block {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .info-block label {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.75rem;
          font-weight: 600;
          font-family: 'Syne', sans-serif;
          letter-spacing: 0.05em;
          color: var(--muted);
          text-transform: uppercase;
        }
        .info-block label em { text-transform: none; font-style: normal; color: var(--error); }
        .copy-row {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: var(--bg);
          border: 1px solid var(--border2);
          border-radius: var(--radius);
          padding: 0.65rem 0.65rem 0.65rem 1rem;
        }
        .copy-row.secret { border-color: rgba(255,106,155,0.3); }
        .mono {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.78rem;
          flex: 1;
          min-width: 0;
        }
        .truncate {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .hint {
          font-size: 0.75rem;
          color: var(--muted);
          font-style: italic;
        }

        /* ── View result ── */
        .view-result {
          background: var(--bg);
          border: 1px solid var(--border2);
          border-radius: var(--radius);
          overflow: hidden;
        }
        .view-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.6rem 1rem;
          border-bottom: 1px solid var(--border);
          font-size: 0.78rem;
          color: var(--muted);
        }
        .view-meta em { font-style: normal; }
        .view-text {
          padding: 1rem;
          font-size: 0.9rem;
          line-height: 1.75;
          white-space: pre-wrap;
          word-break: break-word;
        }

        /* ── Spinner ── */
        .spinner {
          width: 14px; height: 14px;
          border: 2px solid rgba(255,255,255,0.25);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Toasts ── */
        .toast-container {
          position: fixed;
          bottom: 1.5rem;
          right: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          z-index: 999;
        }
        .toast {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1rem;
          border-radius: var(--radius);
          font-size: 0.85rem;
          font-weight: 500;
          backdrop-filter: blur(12px);
          animation: slideIn 0.25s ease;
          max-width: 320px;
        }
        .toast-success {
          background: rgba(74,222,128,0.12);
          border: 1px solid rgba(74,222,128,0.3);
          color: var(--success);
        }
        .toast-error {
          background: rgba(248,113,113,0.12);
          border: 1px solid rgba(248,113,113,0.3);
          color: var(--error);
        }
        .toast button {
          background: none; border: none;
          color: inherit; cursor: pointer;
          opacity: 0.7; margin-left: auto;
          display: flex; align-items: center;
        }
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }

        /* ── Responsive ── */
        @media (max-width: 480px) {
          body { padding: 1.25rem 0.75rem 3rem; }
          .tab-btn span { display: none; }
          .tab-btn { padding: 0.85rem; }
          .tab-content, .result-card { padding: 1.25rem; }
          .input-row { flex-direction: column; align-items: stretch; }
          .input-row .primary-btn { width: 100%; justify-content: center; }
        }
      `}</style>

      {/* Header */}
      <header className="header">
        <div className="wordmark">TextDrop</div>
        <p className="tagline">Share text instantly — no accounts, no friction.</p>
      </header>

      {/* Main card */}
      <div className="card">
        <nav className="tabs">
          {TABS.map(({ id, label, Icon: TabIcon }) => (
            <button
              key={id}
              className={cn("tab-btn", tab === id && "active")}
              onClick={() => setTab(id)}
            >
              <span className="tab-icon"><TabIcon /></span>
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {tab === "share" && <ShareTab onToast={addToast} />}
        {tab === "view"  && <ViewTab  onToast={addToast} />}
        {tab === "edit"  && <EditTab  onToast={addToast} />}
      </div>

      {/* Toasts */}
      <div className="toast-container">
        {toasts.map(t => (
          <Toast key={t.id} message={t.message} type={t.type} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </>
  );
}
