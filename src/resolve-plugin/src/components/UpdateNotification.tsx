import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronUp, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { UpdateInfo, UpdateProgress } from '@xdrop/shared-types';

interface UpdateNotificationProps {
  updateInfo: UpdateInfo | null;
  updateProgress: UpdateProgress | null;
  isInstalling: boolean;
  onInstall: () => void;
  onDismiss: () => void;
}

export const UpdateNotification: React.FC<UpdateNotificationProps> = ({
  updateInfo,
  updateProgress,
  isInstalling,
  onInstall,
  onDismiss,
}) => {
  const [showNotes, setShowNotes] = useState(false);

  const isWorking =
    isInstalling ||
    (updateProgress !== null &&
      ['downloading', 'extracting', 'installing'].includes(updateProgress.stage));

  const isDone = updateProgress !== null && updateProgress.stage === 'completed';

  // Auto-dismiss 3.5 seconds after update finishes
  useEffect(() => {
    if (isDone) {
      const timer = setTimeout(() => {
        onDismiss();
      }, 3500);
      return () => clearTimeout(timer);
    }
  }, [isDone, onDismiss]);

  // STRICT VISIBILITY RULES:
  // 1. Never show if user dismissed it, unless actively working
  if (updateInfo?.isDismissed && !isWorking) {
    return null;
  }

  // 2. Only show if an update is genuinely available, actively installing, or just completed
  const hasUpdate = Boolean(updateInfo?.updateAvailable);
  if (!hasUpdate && !isWorking && !isDone) {
    return null;
  }

  const percent = updateProgress?.percent ?? (isWorking ? 35 : 0);
  const statusMsg = updateProgress?.message || 'Installing update...';

  return (
    <div
      style={{
        margin: '0 12px 6px 12px',
        padding: '6px 10px',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-strong)',
        boxShadow: 'var(--shadow-sm)',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        flexShrink: 0,
        transition: 'all 150ms ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
        }}
      >
        {/* Left: Status icon & version text */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
          {isDone ? (
            <CheckCircle2 size={13} color="var(--success)" strokeWidth={2.2} style={{ flexShrink: 0 }} />
          ) : isWorking ? (
            <Loader2 size={13} color="var(--text-primary)" className="spin" style={{ flexShrink: 0 }} />
          ) : (
            <Sparkles size={13} color="var(--success)" strokeWidth={2} style={{ flexShrink: 0 }} />
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '-0.01em',
              }}
            >
              {isDone
                ? 'Update Complete'
                : isWorking
                ? 'Updating Xdrop...'
                : `Update Available (v${updateInfo?.latestVersion})`}
            </span>

            {!isWorking && !isDone && (
              <span
                className="badge badge-success"
                style={{
                  fontSize: '9px',
                  padding: '1px 5px',
                  fontWeight: 600,
                }}
              >
                New
              </span>
            )}
          </div>
        </div>

        {/* Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
          {!isWorking && !isDone && (
            <>
              {updateInfo?.changelog && (
                <button
                  type="button"
                  onClick={() => setShowNotes(!showNotes)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2px',
                    padding: '2px 4px',
                  }}
                  title="View what's new"
                >
                  {showNotes ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  <span>Notes</span>
                </button>
              )}

              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={onInstall}
                style={{
                  padding: '2px 8px',
                  height: '21px',
                  fontSize: '10px',
                  fontWeight: 600,
                }}
              >
                Update Now
              </button>
            </>
          )}

          {/* Dismiss button is ALWAYS accessible when not actively downloading */}
          {!isWorking && (
            <button
              type="button"
              onClick={onDismiss}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-xs)',
              }}
              title="Close update notification"
            >
              <X size={12} strokeWidth={2} />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar when installing */}
      {isWorking && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginTop: '2px' }}>
          <div
            style={{
              height: '3px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '2px',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, Math.max(0, percent))}%`,
                backgroundColor: 'var(--success)',
                transition: 'width 250ms ease-out',
                borderRadius: '2px',
              }}
            />
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '9.5px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {statusMsg}
            </span>
            <span>{percent}%</span>
          </div>
        </div>
      )}

      {/* Expandable Release Notes */}
      {showNotes && updateInfo?.changelog && !isWorking && (
        <div
          style={{
            marginTop: '3px',
            padding: '6px 8px',
            borderRadius: 'var(--radius-xs)',
            backgroundColor: 'var(--bg-primary)',
            border: '1px solid var(--border-subtle)',
            fontSize: '10px',
            color: 'var(--text-secondary)',
            lineHeight: 1.4,
            maxHeight: '90px',
            overflowY: 'auto',
          }}
        >
          {updateInfo.changelog}
        </div>
      )}
    </div>
  );
};
