import React from 'react';
import { RefreshCw, Film, Layers, Radio, Sparkles } from 'lucide-react';
import { useEditorContext } from '../context/EditorContext';
import logoImg from '../assets/logo.png';

export const Header: React.FC = () => {
  const {
    activeEditor,
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
        shortLabel: 'AE',
        icon: <Sparkles size={11} strokeWidth={2.2} />,
      };
    }
    if (activeEditor === 'premiere') {
      return {
        label: 'Premiere Pro',
        shortLabel: 'Premiere',
        icon: <Layers size={11} strokeWidth={2.2} />,
      };
    }
    if (activeEditor === 'audition') {
      return {
        label: 'Audition',
        shortLabel: 'Audition',
        icon: <Radio size={11} strokeWidth={2.2} />,
      };
    }
    return {
      label: 'DaVinci Resolve',
      shortLabel: 'Resolve',
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
        padding: '0 10px',
        height: '34px',
        userSelect: 'none',
        flexShrink: 0,
        gap: '6px',
      }}
    >
      {/* Brand & Connected Editor */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flexShrink: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
          <img
            src={logoImg}
            alt="Xdrop"
            style={{
              width: '16px',
              height: '16px',
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

        {/* Minimal Connected Status Pill */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 7px',
            borderRadius: '10px',
            border: '1px solid var(--border-default)',
            backgroundColor: 'var(--bg-secondary)',
            fontSize: '9.5px',
            fontWeight: 500,
            color: isEditorConnected ? 'var(--text-primary)' : 'var(--text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flexShrink: 1,
            minWidth: 0,
          }}
          title={isEditorConnected ? `${meta.label} connected and ready` : `Connecting to ${meta.label}...`}
        >
          <span
            style={{
              width: '5px',
              height: '5px',
              borderRadius: '50%',
              backgroundColor: isEditorConnected ? 'var(--success)' : 'var(--text-disabled)',
              flexShrink: 0,
            }}
          />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {meta.shortLabel}
          </span>
        </div>
      </div>

      {/* Right Sequence / Project context & Refresh */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
        {(activeProjectName || activeSequenceOrTimeline) && (
          <span
            style={{
              display: 'inline-block',
              maxWidth: '120px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: 'var(--text-muted)',
              padding: '1px 5px',
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
          onClick={() => { refreshEditorsStatus(); }}
          disabled={isRefreshing}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            padding: 0,
            borderRadius: '4px',
            border: '1px solid transparent',
            backgroundColor: 'transparent',
            color: isRefreshing ? 'var(--text-primary)' : 'var(--text-muted)',
            cursor: isRefreshing ? 'default' : 'pointer',
            transition: 'all 120ms ease',
          }}
          title="Refresh editor connection"
        >
          <span className={isRefreshing ? 'spin' : ''} style={{ display: 'flex' }}>
            <RefreshCw size={12} strokeWidth={2} />
          </span>
        </button>
      </div>
    </header>
  );
};
