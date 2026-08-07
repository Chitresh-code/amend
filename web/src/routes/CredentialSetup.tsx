import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { createCredential } from '../lib/credentialsApi';
import { PROVIDERS } from '../lib/providers';
import './Login.css';

export function CredentialSetup() {
  const navigate = useNavigate();
  const { completeCredentialSetup } = useAuth();

  const [providerKey, setProviderKey] = useState<string | null>(null);
  const [modelId, setModelId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedProvider = PROVIDERS.find((p) => p.key === providerKey) ?? null;

  async function handleAddCredential() {
    if (!providerKey || !modelId || !apiKey) return;
    setError(null);
    setSubmitting(true);
    try {
      await createCredential(providerKey, modelId, apiKey);
      completeCredentialSetup();
      navigate('/chat');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Network error. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Connect a model</h1>
        <p className="login-subhead">
          Amend uses your own model provider credentials. Add one now, or skip and add it later
          from Settings.
        </p>

        <label className="login-field">
          <span>Provider</span>
          <select
            value={providerKey ?? ''}
            onChange={(e) => {
              setProviderKey(e.target.value || null);
              setModelId(null);
            }}
          >
            <option value="">Select a provider</option>
            {PROVIDERS.map((p) => (
              <option key={p.key} value={p.key}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <label className="login-field">
          <span>Model</span>
          <select
            value={modelId ?? ''}
            onChange={(e) => setModelId(e.target.value || null)}
            disabled={!selectedProvider}
          >
            <option value="">Select a model</option>
            {selectedProvider?.models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label className="login-field">
          <span>API key</span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
          />
        </label>

        {error && <p className="login-error">{error}</p>}

        <button
          type="button"
          className="login-submit"
          disabled={!providerKey || !modelId || !apiKey || submitting}
          onClick={handleAddCredential}
        >
          {submitting ? 'Adding...' : 'Add and continue'}
        </button>

        <button
          type="button"
          className="login-skip"
          onClick={() => {
            completeCredentialSetup();
            navigate('/chat');
          }}
        >
          Set up later
        </button>
      </div>
    </div>
  );
}
