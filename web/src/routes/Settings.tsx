import { useEffect, useState } from 'react';
import { ApiError } from '../lib/api';
import {
  deleteCredential,
  listCredentials,
  setDefaultCredential,
  type Credential,
} from '../lib/credentialsApi';
import './Settings.css';

export function Settings() {
  const [credentials, setCredentials] = useState<Credential[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyProvider, setBusyProvider] = useState<string | null>(null);

  function reload() {
    listCredentials()
      .then(setCredentials)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Network error.'));
  }

  useEffect(reload, []);

  async function handleSetDefault(provider: string) {
    setBusyProvider(provider);
    try {
      await setDefaultCredential(provider);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Network error.');
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
      setError(err instanceof ApiError ? err.message : 'Network error.');
    } finally {
      setBusyProvider(null);
    }
  }

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <p className="settings-subhead">
        API keys, account, and retrieval settings are not yet implemented.
      </p>

      <section className="settings-section">
        <h2>Model credentials</h2>

        {error && <p className="settings-error">{error}</p>}

        {credentials === null && !error && <p className="settings-muted">Loading...</p>}
        {credentials?.length === 0 && (
          <p className="settings-muted">No model credentials configured yet.</p>
        )}

        {credentials && credentials.length > 0 && (
          <ul className="credential-list">
            {credentials.map((cred) => (
              <li key={cred.provider} className="credential-row">
                <div>
                  <div className="credential-provider">{cred.provider}</div>
                  <div className="credential-detail">
                    {cred.model_id} &middot; ...{cred.key_suffix}
                  </div>
                </div>
                <div className="credential-actions">
                  {cred.is_default ? (
                    <span className="credential-default-badge">Default</span>
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
    </div>
  );
}
