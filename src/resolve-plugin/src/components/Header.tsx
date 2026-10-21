import React from 'react';
import { RefreshCw, Sparkles, Film, Layers, Radio } from 'lucide-react';
import { useEditorContext } from '../context/EditorContext';
import logoImg from '../assets/logo.png';

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

  const getEditorMeta = () => {
    if (activeEditor === 'aftereffects') {
      return {
        label: 'After Effects',
        icon: <Sparkles size={11} strokeWidth={2.2} />,
      };
    }
    if (activeEditor === 'premiere') {
      return {
        label: 'Premiere Pro',
        icon: <Layers size={11} strokeWidth={2.2} />,
      };
    }
    if (activeEditor === 'audition') {
      return {
        label: 'Audition',
        icon: <Radio size={11} strokeWidth={2.2} />,
      };
    }
    return {
      label: 'DaVinci Resolve',
      icon: <Film size={11} strokeWidth={2.2} />,
    };
  };

  const meta = getEditorMeta();

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'var(--bg-primary)',
        borderBottom: '1px solid var(--border-default)',
        padding: '0 12px',
        height: '38px',
        userSelect: 'none',
        flexShrink: 0,
        gap: '8px',
      }}
    >
      {/* Brand & Connected Editor */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <img
            src={logoImg}
            alt="Xdrop"
            style={{
              width: '18px',
              height: '18px',
              objectFit: 'contain',
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '-0.02em',
              color: 'var(--text-primary)',
            }}
          >
            Xdrop
          </span>
        </div>

        {/* Studio Status Pill with subtle breathing indicator */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            padding: '2px 8px',
            borderRadius: '12px',
            border: '1px solid var(--border-default)',
            backgroundColor: 'var(--bg-secondary)',
            fontSize: '10px',
            fontWeight: 500,
            color: isEditorConnected ? 'var(--text-primary)' : 'var(--text-muted)',
            transition: 'all 0.15s ease',
          }}
          title={isEditorConnected ? `${activeEditorName} connected and ready` : `Waiting for ${activeEditorName} connection`}
        >
          <span
            className={isEditorConnected ? 'pulse-dot' : ''}
            style={{
              width: '5px',
              height: '5px',
              borderRadius: '50%',
              backgroundColor: isEditorConnected ? 'var(--success)' : 'var(--text-disabled)',
              flexShrink: 0,
            }}
          />
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ color: isEditorConnected ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
              {meta.icon}
            </span>
            <span>{meta.label}</span>
          </span>
        </div>
      </div>

      {/* Right Project / Sequence Context & Sync */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flexShrink: 0 }}>
        {(activeProjectName || activeSequenceOrTimeline) && (
          <span
            style={{
              display: 'inline-block',
              maxWidth: '160px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--font-mono)',
              fontSize: '9.5px',
              color: 'var(--text-muted)',
              padding: '2px 6px',
              borderRadius: 'var(--radius-xs)',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
            title={`${activeProjectName || ''}${activeSequenceOrTimeline ? ` • ${activeSequenceOrTimeline}` : ''}`}
          >
            {activeSequenceOrTimeline || activeProjectName}
          </span>
        )}

        <button
          type="button"
          onClick={() => refreshEditorsStatus()}
          disabled={isRefreshing}
          className="btn btn-sm btn-ghost"
          style={{
            padding: '3px 6px',
            height: '24px',
            borderRadius: 'var(--radius-xs)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10px',
            color: 'var(--text-muted)',
          }}
          title="Refresh editor connection and project status"
        >
          <RefreshCw
            size={11}
            strokeWidth={2}
            className={isRefreshing ? 'spin' : ''}
          />
        </button>
      </div>
    </header>
  );
};
