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
        color: 'var(--color-ae)',
        icon: <Sparkles size={11} strokeWidth={2.5} />,
      };
    }
    if (activeEditor === 'premiere') {
      return {
        label: 'Premiere Pro',
        color: 'var(--color-premiere)',
        icon: <Layers size={11} strokeWidth={2.5} />,
      };
    }
    return {
      label: 'DaVinci Resolve',
      color: 'var(--color-resolve)',
      icon: <Film size={11} strokeWidth={2.5} />,
    };
  };

  const badge = getEditorBadge();

  return (
    <header
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-primary)',
        borderBottom: '1.5px solid #000000',
        padding: '8px 12px',
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
              width: '24px',
              height: '24px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-tertiary)',
              border: '1.5px solid #000000',
              boxShadow: '1.5px 1.5px 0px #000000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-primary)',
              flexShrink: 0,
            }}
          >
            <Sparkles size={13} strokeWidth={2.5} />
          </div>

          <span
            style={{
              fontSize: '13px',
              fontWeight: 900,
              letterSpacing: '-0.02em',
              color: '#ffffff',
              whiteSpace: 'nowrap',
            }}
          >
            XDROP
          </span>

          {/* Auto-detected Editor Status Pill */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 7px',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid #000000',
              backgroundColor: 'var(--bg-secondary)',
              boxShadow: '1px 1px 0px #000000',
              fontSize: '10px',
              fontWeight: 800,
              color: badge.color,
            }}
            title={isEditorConnected ? `${activeEditorName} connected` : `${activeEditorName} waiting for connection`}
          >
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                backgroundColor: isEditorConnected ? 'var(--success)' : 'var(--warning)',
                flexShrink: 0,
              }}
            />
            <span>{badge.label}</span>
          </div>
        </div>

        {/* Right Tools: Clean Sync / Refresh button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          <button
            onClick={() => refreshEditorsStatus()}
            disabled={isRefreshing}
            className="btn btn-sm"
            style={{
              padding: '4px 6px',
              backgroundColor: 'var(--bg-secondary)',
              border: '1.5px solid #000000',
              boxShadow: '1.5px 1.5px 0px #000000',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '10px',
            }}
            title="Sync connection and project status"
          >
            <RefreshCw
              size={11}
              strokeWidth={2.5}
              className={isRefreshing ? 'spin' : ''}
              style={{ color: '#ffffff' }}
            />
            <span style={{ color: 'var(--text-secondary)' }}>Sync</span>
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
            fontSize: '10px',
            color: 'var(--text-muted)',
            padding: '0 2px',
            minWidth: 0,
          }}
        >
          <span
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '9.5px',
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
