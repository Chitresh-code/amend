import { useTheme } from '../lib/theme';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
      style={{
        border: '1px solid var(--border)',
        background: 'var(--surface)',
        color: 'var(--text)',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 13,
        cursor: 'pointer',
      }}
    >
      {theme === 'dark' ? 'Dark' : 'Light'}
    </button>
  );
}
