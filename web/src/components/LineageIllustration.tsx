import { useState } from 'react';
import './LineageIllustration.css';

interface LineageNode {
  id: string;
  x: number;
  y: number;
  label: string;
  detail: string;
  current?: boolean;
}

const NODES: LineageNode[] = [
  { id: 'a', x: 20, y: 100, label: 'RBI/2015-16', detail: 'Circular · superseded' },
  { id: 'b', x: 110, y: 55, label: 'RBI/2019-20', detail: 'Amendment · superseded' },
  { id: 'c', x: 200, y: 90, label: 'RBI/2021-22', detail: 'Clarification · superseded' },
  { id: 'd', x: 290, y: 40, label: 'RBI/2023-24/58', detail: 'Amendment · superseded' },
  { id: 'e', x: 380, y: 70, label: 'RBI/2023-24/102', detail: 'Master direction · current', current: true },
];

export function LineageIllustration() {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="lineage-illustration">
      <svg viewBox="0 0 420 150" className="lineage-illustration-lines">
        {NODES.slice(0, -1).map((node, i) => {
          const next = NODES[i + 1];
          return (
            <line
              key={node.id}
              x1={node.x}
              y1={node.y}
              x2={next.x}
              y2={next.y}
              stroke="var(--border)"
              strokeWidth={1.5}
              strokeDasharray={next.current ? undefined : '4 4'}
            />
          );
        })}
      </svg>
      {NODES.map((node) => (
        <div
          key={node.id}
          className={`lineage-illustration-node${node.current ? ' is-current' : ''}`}
          style={{ left: node.x, top: node.y }}
          onMouseEnter={() => setHovered(node.id)}
          onMouseLeave={() => setHovered((h) => (h === node.id ? null : h))}
        >
          {hovered === node.id && (
            <div className="lineage-illustration-tooltip">
              <div className="lineage-illustration-tooltip-ref">{node.label}</div>
              <div>{node.detail}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
