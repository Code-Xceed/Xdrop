import React, { useState } from 'react';
import { ArrowUpCircle, X, ChevronDown, ChevronUp, CheckCircle, Loader2 } from 'lucide-react';
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

  const percent = updateProgress?.percent ?? (isWorking ? 30 : 0);
  const statusMsg = updateProgress?.message || 'Installing update...';

  return (
    <div
      style={{
        margin: '6px 12px 2px 12px',
        padding: '9px 12px',
        borderRadius: '8px',
        backgroundColor: 'rgba(20, 24, 33, 0.96)',
        border: '1px solid rgba(52, 211, 153, 0.28)',
        boxShadow: '0 4px 18px rgba(0, 0, 0, 0.35)',
        backdropFilter: 'blur(10px)',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        animation: 'fadeIn 0.2s ease-out',
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
        {/* Left: Badge + Version Headline */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          {isDone ? (
            <CheckCircle size={15} color="#34d399" style={{ flexShrink: 0 }} />
          ) : isWorking ? (
            <Loader2 size={15} color="#38bdf8" className="animate-spin" style={{ flexShrink: 0 }} />
          ) : (
            <ArrowUpCircle size={15} color="#34d399" style={{ flexShrink: 0 }} />
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
                style={{
                  fontSize: '10px',
                  padding: '1px 5px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(52, 211, 153, 0.12)',
                  color: '#34d399',
                  border: '1px solid rgba(52, 211, 153, 0.25)',
                  fontWeight: 600,
                }}
              >
                New
              </span>
            )}
          </div>
        </div>

        {/* Right Actions: Update button & dismiss */}
        {!isWorking && !isDone && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            {updateInfo.changelog && (
              <button
                type="button"
                onClick={() => setShowNotes(!showNotes)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '2px',
                  padding: '2px 4px',
                }}
                title="View what's new"
              >
                {showNotes ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                <span>Notes</span>
              </button>
            )}

            <button
              type="button"
              onClick={onInstall}
              style={{
                backgroundColor: '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '5px',
                padding: '3px 9px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#059669')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#10b981')}
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
                borderRadius: '4px',
              }}
              title="Later"
            >
              <X size={13} />
            </button>
          </div>
        )}
      </div>

      {/* Progress indicator during download / installation */}
      {isWorking && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '2px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '10px',
              color: 'var(--text-secondary)',
            }}
          >
            <span>{statusMsg}</span>
            <span style={{ fontWeight: 600 }}>{percent}%</span>
          </div>

          <div
            style={{
              width: '100%',
              height: '4px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '2px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${percent}%`,
                height: '100%',
                backgroundColor: '#34d399',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
        </div>
      )}

      {/* Completion message */}
      {isDone && (
        <div
          style={{
            fontSize: '10px',
            color: '#34d399',
            fontWeight: 500,
          }}
        >
          {statusMsg} Restarting interface...
        </div>
      )}

      {/* Expandable release notes */}
      {showNotes && updateInfo.changelog && !isWorking && !isDone && (
        <div
          style={{
            marginTop: '4px',
            padding: '6px 8px',
            borderRadius: '5px',
            backgroundColor: 'rgba(0, 0, 0, 0.25)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            fontSize: '10px',
            lineHeight: '1.4',
            color: 'var(--text-secondary)',
            maxHeight: '80px',
            overflowY: 'auto',
          }}
        >
          {updateInfo.changelog}
        </div>
      )}
    </div>
  );
};
