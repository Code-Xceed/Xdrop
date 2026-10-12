import React from 'react';
import { RefreshCw, Sparkles, Film, Layers } from 'lucide-react';
import { useEditorContext } from '../context/EditorContext';

export const Header: React.FC = () => {
  const {
    activeEditor,
    activeEditorName,
    activeProjectName,
    activeSequenceOrTimeline,
    isEditorConnected,
    refreshEditorsStatus,
    isRefreshing,
  } = useEditorContext();

  const getEditorBadge = () => {
    if (activeEditor === 'aftereffects') {
      return {
        label: 'After Effects',
        icon: <Sparkles size={11} strokeWidth={2} />,
      };
    }
    if (activeEditor === 'premiere') {
      return {
        label: 'Premiere Pro',
        icon: <Layers size={11} strokeWidth={2} />,
      };
    }
    return {
      label: 'DaVinci Resolve',
      icon: <Film size={11} strokeWidth={2} />,
    };
  };

  const badge = getEditorBadge();

  return (
    <header
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-primary)',
        borderBottom: '1px solid var(--border-default)',
        padding: '7px 12px',
        gap: '4px',
        userSelect: 'none',
      }}
    >
      {/* Top Bar: Brand + Auto-detected Editor Status + Tools */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          width: '100%',
        }}
      >
        {/* Brand & Connected Editor Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flexShrink: 0 }}>
          <div
            style={{
              width: '22px',
              height: '22px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-primary)',
              flexShrink: 0,
            }}
          >
            <Sparkles size={12} strokeWidth={2} />
          </div>

          <span
            style={{
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
            }}
          >
            XDROP
          </span>

          {/* Auto-detected Editor Status Pill (Monochromatic Minimalist) */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '2px 7px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--border-default)',
              backgroundColor: 'var(--bg-secondary)',
              fontSize: '10px',
              fontWeight: 500,
              color: 'var(--text-secondary)',
            }}
            title={isEditorConnected ? `${activeEditorName} connected` : `${activeEditorName} waiting for connection`}
          >
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                backgroundColor: isEditorConnected ? 'var(--success)' : 'var(--text-muted)',
                flexShrink: 0,
              }}
            />
            <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
              {badge.icon}
              {badge.label}
            </span>
          </div>
        </div>

        {/* Right Tools: Clean Sync / Refresh button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          <button
            onClick={() => refreshEditorsStatus()}
            disabled={isRefreshing}
            className="btn btn-sm btn-ghost"
            style={{
              padding: '3px 7px',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '10.5px',
              color: 'var(--text-secondary)',
            }}
            title="Sync connection and project status"
          >
            <RefreshCw
              size={11}
              strokeWidth={2}
              className={isRefreshing ? 'spin' : ''}
              style={{ color: 'var(--text-muted)' }}
            />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Slim Project Context Sub-bar */}
      {(activeProjectName || activeSequenceOrTimeline) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '9.5px',
            color: 'var(--text-muted)',
            padding: '0 2px',
            minWidth: 0,
          }}
        >
          <span
            style={{
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}
            title={
              activeSequenceOrTimeline
                ? `${activeProjectName || 'Project'} • ${activeSequenceOrTimeline}`
                : activeProjectName || 'Ready'
            }
          >
            {activeProjectName || 'Project Ready'}
            {activeSequenceOrTimeline ? ` • ${activeSequenceOrTimeline}` : ''}
          </span>
        </div>
      )}
    </header>
  );
};
