import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  deleteConversation,
  listConversations,
  setConversationPinned,
  type Conversation,
} from '../lib/conversationsApi';
import './Chat.css';

const SUGGESTIONS = [
  'What are the current KYC requirements for onboarding a corporate customer?',
  'Has the outsourcing framework for NBFCs changed in the last year?',
  'What disclosures does SEBI require for related-party transactions?',
];

export function Chat() {
  const { user, logout } = useAuth();

  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');

  function reload() {
    listConversations()
      .then(setConversations)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Network error.'));
  }

  useEffect(reload, []);

  async function handleTogglePin(conversation: Conversation) {
    setBusyId(conversation.conversation_id);
    try {
      await setConversationPinned(conversation.conversation_id, !conversation.pinned);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Network error.');
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(conversation: Conversation) {
    setBusyId(conversation.conversation_id);
    try {
      await deleteConversation(conversation.conversation_id);
      if (selectedId === conversation.conversation_id) setSelectedId(null);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Network error.');
    } finally {
      setBusyId(null);
    }
  }

  function handleNewQuery() {
    setSelectedId(null);
    setDraft('');
  }

  const filtered = (conversations ?? []).filter((c) =>
    (c.title ?? '').toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="chat-page">
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <span className="chat-user-email">{user?.email}</span>
          <button type="button" className="chat-new-query" onClick={handleNewQuery}>
            New query
          </button>
        </div>

        <input
          type="search"
          className="chat-search"
          placeholder="Search conversations"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {error && <p className="chat-error">{error}</p>}
        {conversations === null && !error && <p className="chat-muted">Loading...</p>}
        {conversations?.length === 0 && (
          <p className="chat-muted">No conversations yet. Start one below.</p>
        )}
        {conversations !== null && conversations.length > 0 && filtered.length === 0 && (
          <p className="chat-muted">No conversations match "{search}".</p>
        )}

        <ul className="chat-conversation-list">
          {filtered.map((c) => (
            <li
              key={c.conversation_id}
              className={`chat-conversation-row ${c.conversation_id === selectedId ? 'selected' : ''}`}
            >
              <button
                type="button"
                className="chat-conversation-title"
                onClick={() => setSelectedId(c.conversation_id)}
              >
                {c.pinned && <span className="chat-pin-marker">Pinned</span>}
                {c.title ?? 'Untitled conversation'}
              </button>
              <div className="chat-conversation-actions">
                <button
                  type="button"
                  disabled={busyId === c.conversation_id}
                  onClick={() => handleTogglePin(c)}
                >
                  {c.pinned ? 'Unpin' : 'Pin'}
                </button>
                <button
                  type="button"
                  disabled={busyId === c.conversation_id}
                  onClick={() => handleDelete(c)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>

        <div className="chat-sidebar-footer">
          <Link to="/settings">Settings</Link>
          <button type="button" onClick={() => logout()}>
            Log out
          </button>
        </div>
      </aside>

      <main className="chat-main">
        {/* ponytail: query submission and answer rendering ship with epic I;
            this empty state only captures a draft, it cannot submit yet. */}
        <div className="chat-empty-state">
          <h1>What would you like to know?</h1>
          <textarea
            className="chat-input"
            placeholder="Ask about a regulatory requirement..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="chat-suggestions">
            {SUGGESTIONS.map((s) => (
              <button
                type="button"
                key={s}
                className="chat-suggestion-chip"
                onClick={() => setDraft(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
