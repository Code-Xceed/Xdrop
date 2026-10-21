import React, { useState } from 'react';
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

  if (!updateInfo || !updateInfo.updateAvailable || updateInfo.isDismissed) {
    return null;
  }

  const isWorking =
    isInstalling ||
    (updateProgress &&
      ['downloading', 'extracting', 'installing'].includes(updateProgress.stage));

  const isDone = updateProgress && updateProgress.stage === 'completed';
  const percent = updateProgress?.percent ?? (isWorking ? 35 : 0);
  const statusMsg = updateProgress?.message || 'Installing update...';

  return (
    <div
      style={{
        margin: '0 10px 6px 10px',
        padding: '8px 10px',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-strong)',
        boxShadow: 'var(--shadow-sm)',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        flexShrink: 0,
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
        {/* Left: Indicator & Version */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
          {isDone ? (
            <CheckCircle2 size={14} color="var(--success)" style={{ flexShrink: 0 }} />
          ) : isWorking ? (
            <Loader2 size={14} color="var(--text-primary)" className="spin" style={{ flexShrink: 0 }} />
          ) : (
            <Sparkles size={14} color="var(--success)" style={{ flexShrink: 0 }} />
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}
            >
              {isDone
                ? 'Update Complete'
                : isWorking
                ? 'Updating Xdrop...'
                : `Update Available (v${updateInfo.latestVersion})`}
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
        {!isWorking && !isDone && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
            {updateInfo.changelog && (
              <button
                type="button"
                onClick={() => setShowNotes(!showNotes)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '10.5px',
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
                height: '22px',
                fontSize: '10.5px',
                fontWeight: 600,
              }}
            >
              Update Now
            </button>

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
              }}
              title="Dismiss notification"
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Progress Bar when installing */}
      {isWorking && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '2px' }}>
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
      {showNotes && updateInfo.changelog && !isWorking && (
        <div
          style={{
            marginTop: '4px',
            padding: '6px 8px',
            borderRadius: 'var(--radius-xs)',
            backgroundColor: 'var(--bg-primary)',
            border: '1px solid var(--border-subtle)',
            fontSize: '10.5px',
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
