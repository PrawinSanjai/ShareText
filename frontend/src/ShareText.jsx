import { useEffect, useMemo, useState } from "react";
import {
  createText,
  deleteText,
  readText,
  readTextBySecret,
  updateText,
} from "./api/shareTextApi.js";
import { CopyButton } from "./components/CopyButton.jsx";
import { Spinner } from "./components/Spinner.jsx";
import { Tabs } from "./components/Tabs.jsx";
import { ToastStack } from "./components/ToastStack.jsx";
import {
  EditIcon,
  EyeIcon,
  KeyIcon,
  LinkIcon,
  SendIcon,
  TrashIcon,
} from "./components/icons.jsx";
import { useToasts } from "./hooks/useToasts.js";
import "./Textie.css";

const TABS = [
  { id: "share", label: "Share", Icon: SendIcon },
  { id: "view", label: "View", Icon: EyeIcon },
  { id: "manage", label: "Manage", Icon: KeyIcon },
];

function Field({ children, icon, label }) {
  return (
    <label className="field">
      <span className="field-label">
        {icon}
        {label}
      </span>
      {children}
    </label>
  );
}

function TextAreaField({ label, value, onChange, placeholder }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className="textarea-shell">
        <textarea
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          rows={10}
          value={value}
        />
        <span className="char-count">{value.length}</span>
      </span>
    </label>
  );
}

function SharePanel({ onToast }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const shareUrl = useMemo(() => {
    if (!result?.text_id) return "";
    return `${window.location.origin}?id=${result.text_id}`;
  }, [result]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!text.trim()) return;

    setSubmitting(true);
    try {
      const data = await createText(text);
      setResult(data);
      onToast("Text shared");
    } catch (error) {
      onToast(error.message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <section className="panel-body">
        <div className="result-header">
          <span className="status-pill">Shared</span>
          <button
            className="quiet-button"
            onClick={() => {
              setResult(null);
              setText("");
            }}
            type="button"
          >
            New text
          </button>
        </div>

        <ResultRow icon={<LinkIcon />} label="Share link" value={shareUrl} />
        <ResultRow icon={<KeyIcon />} label="Secret key" value={result.secret_key} />
        <ResultRow label="Text ID" value={result.text_id} />
      </section>
    );
  }

  return (
    <form className="panel-body" onSubmit={handleSubmit}>
      <TextAreaField
        label="Text"
        onChange={setText}
        placeholder="Paste text here"
        value={text}
      />

      <button className="primary-button" disabled={isSubmitting || !text.trim()}>
        {isSubmitting ? <Spinner /> : <SendIcon />}
        Generate link
      </button>
    </form>
  );
}

function ResultRow({ icon = null, label, value }) {
  return (
    <div className="result-row">
      <span className="result-label">
        {icon}
        {label}
      </span>
      <div className="copy-surface">
        <span className="mono truncate">{value}</span>
        <CopyButton text={value} />
      </div>
    </div>
  );
}

function ViewPanel({ initialTextId, onToast }) {
  const [textId, setTextId] = useState(initialTextId);
  const [result, setResult] = useState(null);
  const [isLoading, setLoading] = useState(false);

  async function handleRead(event) {
    event?.preventDefault();
    if (!textId.trim()) return;

    setLoading(true);
    setResult(null);
    try {
      const data = await readText(textId.trim());
      setResult(data.result);
    } catch (error) {
      onToast(error.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!initialTextId) return;
    handleRead();
    // The initial URL value should trigger exactly one automatic fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTextId]);

  return (
    <form className="panel-body" onSubmit={handleRead}>
      <div className="inline-form">
        <Field icon={<LinkIcon />} label="Text ID">
          <input
            className="mono"
            onChange={(event) => setTextId(event.target.value)}
            placeholder="Paste text ID"
            type="text"
            value={textId}
          />
        </Field>
        <button className="primary-button compact" disabled={isLoading || !textId.trim()}>
          {isLoading ? <Spinner /> : <EyeIcon />}
          View
        </button>
      </div>

      {result && (
        <article className="text-result">
          <div className="text-result-toolbar">
            <span className="mono truncate">{textId}</span>
            <CopyButton label="Copy text" text={result} />
          </div>
          <p>{result}</p>
        </article>
      )}
    </form>
  );
}

function ManagePanel({ onToast }) {
  const [secretKey, setSecretKey] = useState("");
  const [textId, setTextId] = useState("");
  const [text, setText] = useState("");
  const [isDeleting, setDeleting] = useState(false);
  const [isLoading, setLoading] = useState(false);
  const [isSaving, setSaving] = useState(false);

  async function handleLoad() {
    if (!secretKey.trim()) return;

    setLoading(true);
    try {
      const data = await readTextBySecret(secretKey.trim());
      setText(data.result);
      setTextId(data.text_id);
      onToast("Text loaded");
    } catch (error) {
      onToast(error.message, "error");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdate(event) {
    event.preventDefault();
    if (!secretKey.trim() || !text.trim()) return;

    setSaving(true);
    try {
      await updateText({ text, secretKey: secretKey.trim() });
      onToast("Text updated");
    } catch (error) {
      onToast(error.message, "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!secretKey.trim()) return;

    setDeleting(true);
    try {
      await deleteText(secretKey.trim());
      setText("");
      setTextId("");
      setSecretKey("");
      onToast("Text deleted");
    } catch (error) {
      onToast(error.message, "error");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <form className="panel-body" onSubmit={handleUpdate}>
      <Field icon={<KeyIcon />} label="Secret key">
        <input
          className="mono"
          onChange={(event) => setSecretKey(event.target.value)}
          placeholder="Paste secret key"
          type="password"
          value={secretKey}
        />
      </Field>

      <button
        className="quiet-button load-button"
        disabled={isLoading || !secretKey.trim()}
        onClick={handleLoad}
        type="button"
      >
        {isLoading ? <Spinner /> : <EyeIcon />}
        Load text
      </button>

      {textId && (
        <div className="copy-surface">
          <span className="mono truncate">{textId}</span>
          <CopyButton label="Copy ID" text={textId} />
        </div>
      )}

      <TextAreaField
        label="Text"
        onChange={setText}
        placeholder="Load text or enter replacement text"
        value={text}
      />

      <div className="action-row">
        <button
          className="primary-button"
          disabled={isSaving || !secretKey.trim() || !text.trim()}
        >
          {isSaving ? <Spinner /> : <EditIcon />}
          Update
        </button>
        <button
          className="danger-button"
          disabled={isDeleting || !secretKey.trim()}
          onClick={handleDelete}
          type="button"
        >
          {isDeleting ? <Spinner /> : <TrashIcon />}
          Delete
        </button>
      </div>
    </form>
  );
}

export default function ShareText() {
  const initialTextId = useMemo(() => {
    return new URLSearchParams(window.location.search).get("id") || "";
  }, []);

  const [activeTab, setActiveTab] = useState(initialTextId ? "view" : "share");
  const { dismissToast, showToast, toasts } = useToasts();

  return (
    <main className="app-shell">
      <header className="masthead">
        <p className="eyebrow">Textie</p>
        <h1>Share text privately.</h1>
      </header>

      <section className="tool-panel">
        <Tabs activeTab={activeTab} items={TABS} onChange={setActiveTab} />
        {activeTab === "share" && <SharePanel onToast={showToast} />}
        {activeTab === "view" && (
          <ViewPanel initialTextId={initialTextId} onToast={showToast} />
        )}
        {activeTab === "manage" && <ManagePanel onToast={showToast} />}
      </section>

      <ToastStack onDismiss={dismissToast} toasts={toasts} />
    </main>
  );
}
