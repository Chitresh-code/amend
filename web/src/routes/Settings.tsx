import { useEffect, useState, type FormEvent } from 'react';
import { ApiError } from '../lib/api';
import { listApiKeys, revokeApiKey, type ApiKey } from '../lib/apiKeysApi';
import { useAuth } from '../lib/auth';
import {
  deleteCredential,
  listCredentials,
  setDefaultCredential,
  type Credential,
} from '../lib/credentialsApi';
import {
  listEmbeddingIndexes,
  registerEmbeddingIndex,
  setDefaultEmbeddingIndex,
  type EmbeddingIndex,
} from '../lib/embeddingIndexesApi';
import './Settings.css';

type Tab = 'models' | 'api-keys' | 'account' | 'retrieval';

const TABS: { id: Tab; label: string }[] = [
  { id: 'models', label: 'Models' },
  { id: 'api-keys', label: 'API keys' },
  { id: 'account', label: 'Account' },
  { id: 'retrieval', label: 'Retrieval' },
];

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Network error.';
}

function ModelsTab() {
  const [credentials, setCredentials] = useState<Credential[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyProvider, setBusyProvider] = useState<string | null>(null);

  function reload() {
    listCredentials()
      .then(setCredentials)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(reload, []);

  async function handleSetDefault(provider: string) {
    setBusyProvider(provider);
    try {
      await setDefaultCredential(provider);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleRemove(provider: string) {
    setBusyProvider(provider);
    try {
      await deleteCredential(provider);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyProvider(null);
    }
  }

  return (
    <section className="settings-section">
      <h2>Model credentials</h2>

      {error && <p className="settings-error">{error}</p>}
      {credentials === null && !error && <p className="settings-muted">Loading...</p>}
      {credentials?.length === 0 && (
        <p className="settings-muted">No model credentials configured yet.</p>
      )}

      {credentials && credentials.length > 0 && (
        <ul className="settings-list">
          {credentials.map((cred) => (
            <li key={cred.provider} className="settings-row">
              <div>
                <div className="settings-row-title">{cred.provider}</div>
                <div className="settings-row-detail">
                  {cred.model_id} &middot; ...{cred.key_suffix}
                </div>
              </div>
              <div className="settings-row-actions">
                {cred.is_default ? (
                  <span className="settings-badge">Default</span>
                ) : (
                  <button
                    type="button"
                    disabled={busyProvider === cred.provider}
                    onClick={() => handleSetDefault(cred.provider)}
                  >
                    Set default
                  </button>
                )}
                <button
                  type="button"
                  disabled={busyProvider === cred.provider}
                  onClick={() => handleRemove(cred.provider)}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ApiKeysTab() {
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function reload() {
    listApiKeys()
      .then(setKeys)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(reload, []);

  async function handleRevoke(id: string) {
    setBusyId(id);
    try {
      await revokeApiKey(id);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="settings-section">
      <h2>Amend API keys</h2>
      <p className="settings-subhead">
        Keys are issued by an Amend operator. Self-service key generation isn't available yet.
      </p>

      {error && <p className="settings-error">{error}</p>}
      {keys === null && !error && <p className="settings-muted">Loading...</p>}
      {keys?.length === 0 && <p className="settings-muted">No API keys issued yet.</p>}

      {keys && keys.length > 0 && (
        <ul className="settings-list">
          {keys.map((key) => (
            <li key={key.id} className="settings-row">
              <div>
                <div className="settings-row-title">{key.label}</div>
                <div className="settings-row-detail">sk-amd-&bull;&bull;&bull;&bull;{key.key_suffix}</div>
              </div>
              <div className="settings-row-actions">
                <button
                  type="button"
                  disabled={busyId === key.id}
                  onClick={() => handleRevoke(key.id)}
                >
                  Revoke
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AccountTab() {
  const { user } = useAuth();
  const [showPasswordNote, setShowPasswordNote] = useState(false);

  return (
    <section className="settings-section">
      <h2>Account</h2>
      <div className="settings-list">
        <div className="settings-row settings-row-static">
          <span className="settings-row-title">Email</span>
          <span className="settings-row-detail">{user?.email}</span>
        </div>
        <div className="settings-row settings-row-static">
          <span className="settings-row-title">Organization</span>
          <span className="settings-row-detail">{user?.organization ?? 'Not set'}</span>
        </div>
      </div>
      <button type="button" className="settings-link-button" onClick={() => setShowPasswordNote(true)}>
        Change password
      </button>
      {showPasswordNote && (
        <p className="settings-muted">
          Self-service password changes aren't available yet. Contact your Amend administrator.
        </p>
      )}
    </section>
  );
}

function RetrievalTab() {
  const [indexes, setIndexes] = useState<EmbeddingIndex[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [provider, setProvider] = useState('');
  const [modelId, setModelId] = useState('');
  const [dimension, setDimension] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function reload() {
    listEmbeddingIndexes()
      .then(setIndexes)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(reload, []);

  async function handleSetDefault(id: string) {
    setBusyId(id);
    try {
      await setDefaultEmbeddingIndex(id);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const dim = Number(dimension);
    if (!provider || !modelId || !dim) return;
    setSubmitting(true);
    setError(null);
    try {
      await registerEmbeddingIndex(provider, modelId, dim);
      setProvider('');
      setModelId('');
      setDimension('');
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="settings-section">
      <h2>Embedding indexes</h2>
      <p className="settings-subhead">
        Registering an index records a candidate only; building it (ingestion into a real
        retrieval table) is a separate, offline operator step.
      </p>

      {error && <p className="settings-error">{error}</p>}
      {indexes === null && !error && <p className="settings-muted">Loading...</p>}
      {indexes?.length === 0 && <p className="settings-muted">No embedding indexes registered yet.</p>}

      {indexes && indexes.length > 0 && (
        <ul className="settings-list">
          {indexes.map((idx) => (
            <li key={idx.embedding_model_id} className="settings-row">
              <div>
                <div className="settings-row-title">{idx.embedding_model_id}</div>
                <div className="settings-row-detail">
                  {idx.clause_count.toLocaleString()} clauses &middot;{' '}
                  <span className={`settings-status settings-status-${idx.status}`}>
                    {idx.status}
                  </span>
                </div>
              </div>
              <div className="settings-row-actions">
                {idx.is_default ? (
                  <span className="settings-badge">Default</span>
                ) : (
                  <button
                    type="button"
                    disabled={idx.status !== 'ready' || busyId === idx.embedding_model_id}
                    title={idx.status !== 'ready' ? 'Only a ready index can be set as default' : undefined}
                    onClick={() => handleSetDefault(idx.embedding_model_id)}
                  >
                    Set default
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <form className="settings-add-form" onSubmit={handleAdd}>
        <input
          placeholder="Provider (e.g. voyage)"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
        />
        <input
          placeholder="Model ID (e.g. voyage-law-2)"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
        />
        <input
          type="number"
          placeholder="Dimension"
          value={dimension}
          onChange={(e) => setDimension(e.target.value)}
        />
        <button type="submit" disabled={submitting || !provider || !modelId || !dimension}>
          {submitting ? 'Adding...' : 'Add index'}
        </button>
      </form>
    </section>
  );
}

export function Settings() {
  const [tab, setTab] = useState<Tab>('models');

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <nav className="settings-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`settings-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'models' && <ModelsTab />}
      {tab === 'api-keys' && <ApiKeysTab />}
      {tab === 'account' && <AccountTab />}
      {tab === 'retrieval' && <RetrievalTab />}
    </div>
  );
}
