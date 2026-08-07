import { Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export function Chat() {
  const { user, logout } = useAuth();

  return (
    <div style={{ padding: 48, maxWidth: 640, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{user?.email}</span>
        <div style={{ display: 'flex', gap: 16 }}>
          <Link to="/settings" style={{ fontSize: 13 }}>
            Settings
          </Link>
          <button
            type="button"
            onClick={() => logout()}
            style={{
              border: 'none',
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            Log out
          </button>
        </div>
      </div>
      <h1 style={{ fontSize: 22, marginBottom: 8 }}>Chat</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
        Chat sessions, query submission, and citations (Epics H through J) are not yet
        implemented.
      </p>
    </div>
  );
}
