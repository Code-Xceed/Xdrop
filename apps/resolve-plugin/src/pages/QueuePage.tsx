import React, { useState } from 'react';
import { DownloadJob } from '@xdrop/shared-types';
import { formatBytes } from '@xdrop/utilities';
import { useEditorContext } from '../context/EditorContext';
import {
  cancelDownload,
  retryDownload,
  removeDownload,
  importJobToResolve,
  importJobToPremiere,
  importJobToAfterEffects,
} from '../services/api';
import {
  Film,
  Music,
  CheckCircle2,
  AlertCircle,
  XCircle,
  RotateCcw,
  Trash2,
  ArrowUpRight,
  Zap,
  Check,
} from 'lucide-react';

interface QueuePageProps {
  downloads: DownloadJob[];
  onRefresh: () => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

type EditorTarget = 'resolve' | 'premiere' | 'aftereffects';

export const QueuePage: React.FC<QueuePageProps> = ({
  downloads,
  onRefresh,
  showToast,
}) => {
  const { activeEditor } = useEditorContext();
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'failed'>('all');
  const [selectedEditorMap, setSelectedEditorMap] = useState<Record<string, EditorTarget>>({});
  const [importingId, setImportingId] = useState<string | null>(null);

  // Helper to determine selected editor for a given job
  const getSelectedEditorForJob = (job: DownloadJob): EditorTarget => {
    if (selectedEditorMap[job.id]) {
      return selectedEditorMap[job.id];
    }
    // Auto-detect matching where the user is working
    if (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'resolve') {
      return activeEditor;
    }
    const target = job.targetEditor || (job as any).target_editor;
    if (target === 'premiere' || target === 'aftereffects' || target === 'resolve') {
      return target;
    }
    return 'resolve';
  };

  const handleEditorSelectionChange = (jobId: string, editor: EditorTarget) => {
    setSelectedEditorMap((prev) => ({
      ...prev,
      [jobId]: editor,
    }));
  };

  const handleCancel = async (id: string) => {
    try {
      await cancelDownload(id);
      showToast('Download cancelled.', 'info');
      onRefresh();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await retryDownload(id);
      showToast('Retrying download...', 'info');
      onRefresh();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await removeDownload(id);
      onRefresh();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleTriggerImport = async (jobId: string, target: EditorTarget) => {
    setImportingId(jobId);
    try {
      if (target === 'premiere') {
        const res = await importJobToPremiere(jobId);
        if (res.success) {
          showToast('Imported into Adobe Premiere Pro project bin!', 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import to Premiere Pro. Ensure Premiere is open.', 'error');
        }
      } else if (target === 'aftereffects') {
        const res = await importJobToAfterEffects(jobId);
        if (res.success) {
          showToast('Imported into Adobe After Effects project panel!', 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import to After Effects. Ensure AE is open.', 'error');
        }
      } else {
        const res = await importJobToResolve(jobId);
        if (res.success) {
          showToast(`Imported into DaVinci Resolve: ${res.clipName || 'Media Pool'}`, 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import to Resolve. Ensure Resolve is open.', 'error');
        }
      }
    } catch (e: any) {
      showToast(e.message || 'Import error occurred.', 'error');
    } finally {
      setImportingId(null);
    }
  };

  const activeDownloads = downloads.filter(
    (j) => j.status === 'downloading' || j.status === 'processing' || j.status === 'importing' || j.status === 'queued'
  );
  const completedDownloads = downloads.filter((j) => j.status === 'completed');
  const failedDownloads = downloads.filter((j) => j.status === 'failed' || j.status === 'cancelled');

  const filteredJobs = downloads.filter((j) => {
    if (filter === 'active') return ['downloading', 'processing', 'importing', 'queued'].includes(j.status);
    if (filter === 'completed') return j.status === 'completed';
    if (filter === 'failed') return j.status === 'failed' || j.status === 'cancelled';
    return true;
  });

  if (downloads.length === 0) {
    return (
      <div
        style={{
          maxWidth: '520px',
          margin: '36px auto',
          textAlign: 'center',
          padding: '32px 18px',
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1.5px solid #000000',
          boxShadow: 'var(--neo-shadow-card)',
        }}
      >
        <div
          style={{
            width: '42px',
            height: '42px',
            margin: '0 auto 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-tertiary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-primary)',
            border: '1.5px solid #000000',
            boxShadow: '1.5px 1.5px 0px #000000',
          }}
        >
          <Zap size={22} strokeWidth={2.5} />
        </div>
        <h4 style={{ fontSize: '13.5px', fontWeight: 900, marginBottom: '4px', color: '#ffffff' }}>
          Queue is Empty
        </h4>
        <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
          Paste any video or audio URL in the Import tab to initiate downloads.
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 10px', maxWidth: '820px', margin: '0 auto' }}>
      {/* Filter Chips Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
          gap: '8px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '0.02em', color: '#ffffff' }}>
            DOWNLOAD QUEUE
          </span>
          <span
            style={{
              fontSize: '9.5px',
              fontWeight: 800,
              padding: '1px 5px',
              borderRadius: '2px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid #000000',
              color: 'var(--text-muted)',
            }}
          >
            {downloads.length}
          </span>
        </div>

        {/* Filter Buttons */}
        <div
          style={{
            display: 'flex',
            backgroundColor: 'var(--bg-secondary)',
            padding: '2px',
            borderRadius: 'var(--radius-sm)',
            border: '1.5px solid #000000',
            gap: '2px',
          }}
        >
          {(['all', 'active', 'completed', 'failed'] as const).map((t) => {
            const count =
              t === 'all'
                ? downloads.length
                : t === 'active'
                ? activeDownloads.length
                : t === 'completed'
                ? completedDownloads.length
                : failedDownloads.length;
            const isSel = filter === t;
            return (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className="btn btn-sm"
                style={{
                  border: isSel ? '1px solid #000000' : '1px solid transparent',
                  backgroundColor: isSel ? 'var(--bg-elevated)' : 'transparent',
                  color: isSel ? '#ffffff' : 'var(--text-muted)',
                  padding: '2px 7px',
                  fontSize: '9.5px',
                  fontWeight: isSel ? 800 : 700,
                  boxShadow: isSel ? '1px 1px 0px #000000' : 'none',
                  transform: 'none',
                  textTransform: 'capitalize',
                }}
              >
                {t} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Queue Job Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filteredJobs.map((job) => {
          const isActive =
            job.status === 'downloading' ||
            job.status === 'processing' ||
            job.status === 'importing';
          const isCompleted = job.status === 'completed';
          const isFailed = job.status === 'failed';
          const isCancelled = job.status === 'cancelled';

          const isAudio = job.mediaType === 'audio' || (job as any).media_type === 'audio';
          const progressNum = Number(job.progress ?? 0);
          const safeProgress = isNaN(progressNum) ? 0 : progressNum;
          const downloadedBytes = job.downloadedBytes ?? (job as any).downloaded_bytes ?? 0;
          const totalBytes = job.totalBytes ?? (job as any).total_bytes ?? 0;

          const isResolveImported = Boolean(job.resolveImported ?? (job as any).resolve_imported);
          const isPremiereImported = Boolean(job.premiereImported ?? (job as any).premiere_imported);
          const isAfterEffectsImported = Boolean(job.aftereffectsImported ?? (job as any).aftereffects_imported);

          const errorMsg = job.errorMessage || (job as any).error_message || 'Download failed.';
          const formatStr = (job.format || 'MP4').toUpperCase();

          const wasAutoImportRequested = Boolean(job.autoImport ?? (job as any).auto_import);
          const targetEditor = (job.targetEditor ?? (job as any).target_editor) as EditorTarget | undefined;

          // Determine if this item was automatically imported into its targeted software
          const isAutoImportedComplete = isCompleted && wasAutoImportRequested && (
            (targetEditor === 'resolve' && isResolveImported) ||
            (targetEditor === 'premiere' && isPremiereImported) ||
            (targetEditor === 'aftereffects' && isAfterEffectsImported) ||
            (!targetEditor && (isResolveImported || isPremiereImported || isAfterEffectsImported))
          );

          const currentTarget = getSelectedEditorForJob(job);
          const isCurrentlyImporting = importingId === job.id;

          const isAlreadyImportedInTarget =
            (currentTarget === 'resolve' && isResolveImported) ||
            (currentTarget === 'premiere' && isPremiereImported) ||
            (currentTarget === 'aftereffects' && isAfterEffectsImported);

          return (
            <div
              key={job.id}
              className="panel"
              style={{
                padding: '10px 12px',
                border: '1.5px solid #000000',
                borderLeft: `4px solid ${
                  isActive
                    ? 'var(--accent-primary)'
                    : isCompleted
                    ? 'var(--success)'
                    : isFailed
                    ? 'var(--danger)'
                    : 'var(--border-default)'
                }`,
                backgroundColor: 'var(--bg-secondary)',
                boxShadow: '2px 2px 0px #000000',
                transition: 'all 0.1s ease',
              }}
            >
              {/* Row 1: Icon, Title & Status Badge */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: 'var(--bg-tertiary)',
                      border: '1px solid #000000',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ffffff',
                      flexShrink: 0,
                    }}
                  >
                    {isAudio ? <Music size={13} strokeWidth={2.5} /> : <Film size={13} strokeWidth={2.5} />}
                  </div>

                  <h5
                    style={{
                      fontSize: '12px',
                      fontWeight: 800,
                      color: '#ffffff',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={job.title || 'Untitled Asset'}
                  >
                    {job.title || 'Untitled Asset'}
                  </h5>
                </div>

                {/* Status Indicator */}
                <div style={{ flexShrink: 0 }}>
                  {job.status === 'downloading' && (
                    <span className="badge badge-info" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      <span className="spin">⟳</span> DOWNLOADING
                    </span>
                  )}
                  {job.status === 'processing' && (
                    <span className="badge badge-warning" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      TRANSCODING
                    </span>
                  )}
                  {job.status === 'importing' && (
                    <span className="badge badge-info" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      <span className="spin">⟳</span> IMPORTING
                    </span>
                  )}
                  {job.status === 'queued' && (
                    <span className="badge badge-neutral" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      QUEUED
                    </span>
                  )}
                  {isCompleted && (
                    <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      <CheckCircle2 size={10} strokeWidth={2.5} /> READY
                    </span>
                  )}
                  {isFailed && (
                    <span className="badge badge-danger" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      <AlertCircle size={10} strokeWidth={2.5} /> ERROR
                    </span>
                  )}
                  {isCancelled && (
                    <span className="badge badge-neutral" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      <XCircle size={10} strokeWidth={2.5} /> CANCELLED
                    </span>
                  )}
                </div>
              </div>

              {/* Progress Meter Bar */}
              <div
                style={{
                  width: '100%',
                  height: '6px',
                  backgroundColor: '#000000',
                  borderRadius: '2px',
                  overflow: 'hidden',
                  margin: '8px 0 6px',
                  border: '1px solid #000000',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(100, Math.max(0, safeProgress))}%`,
                    background: isCompleted
                      ? 'var(--success)'
                      : isFailed
                      ? 'var(--danger)'
                      : 'var(--accent-primary)',
                    transition: 'width 0.15s ease',
                  }}
                />
              </div>

              {/* Row 3: Telemetry Line */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  gap: '8px',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    minWidth: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {isActive ? (
                    <span>
                      {safeProgress.toFixed(0)}%
                      {totalBytes > 0
                        ? ` • ${formatBytes(downloadedBytes)} / ${formatBytes(totalBytes)}`
                        : downloadedBytes > 0
                        ? ` • ${formatBytes(downloadedBytes)}`
                        : ''}
                      {job.speed ? ` • ${job.speed}` : ''}
                      {job.eta ? ` • ${job.eta}` : ''}
                    </span>
                  ) : isCompleted ? (
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {formatStr} {job.qualityLabel ? `• ${job.qualityLabel}` : ''} • {formatBytes(downloadedBytes)}
                    </span>
                  ) : isFailed ? (
                    <span style={{ color: 'var(--color-resolve)' }}>{errorMsg}</span>
                  ) : (
                    <span>{formatStr} {job.qualityLabel ? `• ${job.qualityLabel}` : ''}</span>
                  )}
                </div>

                {/* Right Quick Actions (Cancel, Retry, Remove) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                  {isActive && (
                    <button
                      onClick={() => handleCancel(job.id)}
                      className="btn btn-sm btn-danger"
                      style={{ padding: '2px 6px', fontSize: '9.5px' }}
                      title="Cancel download"
                    >
                      Cancel
                    </button>
                  )}

                  {(isFailed || isCancelled) && (
                    <button
                      onClick={() => handleRetry(job.id)}
                      className="btn btn-sm btn-secondary"
                      style={{ padding: '2px 6px', fontSize: '9.5px' }}
                      title="Retry download"
                    >
                      <RotateCcw size={10} />
                      <span>Retry</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleRemove(job.id)}
                    className="btn btn-sm btn-ghost"
                    style={{ padding: '2px 4px' }}
                    title="Remove from queue"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>

              {/* Row 4: COMPLETED IMPORT FLOW (Auto-imported badge OR Manual Import Selector) */}
              {isCompleted && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '8px',
                    paddingTop: '8px',
                    borderTop: '1px solid var(--border-subtle)',
                    gap: '8px',
                    flexWrap: 'wrap',
                  }}
                >
                  {isAutoImportedComplete ? (
                    /* Auto-imported mode: Display completed badge without import dropdown or button */
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span
                        className={
                          targetEditor === 'aftereffects' || isAfterEffectsImported
                            ? 'badge badge-ae'
                            : targetEditor === 'premiere' || isPremiereImported
                            ? 'badge badge-premiere'
                            : 'badge badge-resolve'
                        }
                        style={{
                          fontSize: '9.5px',
                          padding: '3px 8px',
                          fontWeight: 800,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        title="Media was automatically imported into project workspace upon download completion."
                      >
                        <Check size={11} strokeWidth={3} />
                        Auto-imported to {
                          targetEditor === 'aftereffects' || isAfterEffectsImported
                            ? 'After Effects'
                            : targetEditor === 'premiere' || isPremiereImported
                            ? 'Premiere Pro'
                            : 'DaVinci Resolve'
                        }
                      </span>
                    </div>
                  ) : (
                    /* Manual import mode (or deferred auto-import): Show dropdown selector + nearby Import button */
                    <>
                      {/* Left: Already-Imported Status Badges */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                        {isResolveImported && (
                          <span
                            className="badge badge-resolve"
                            style={{ fontSize: '8.5px', padding: '1px 5px' }}
                            title="Imported into DaVinci Resolve"
                          >
                            <Check size={9} strokeWidth={3} /> Resolve
                          </span>
                        )}
                        {isPremiereImported && (
                          <span
                            className="badge badge-premiere"
                            style={{ fontSize: '8.5px', padding: '1px 5px' }}
                            title="Imported into Adobe Premiere Pro"
                          >
                            <Check size={9} strokeWidth={3} /> Premiere
                          </span>
                        )}
                        {isAfterEffectsImported && (
                          <span
                            className="badge badge-ae"
                            style={{ fontSize: '8.5px', padding: '1px 5px' }}
                            title="Imported into Adobe After Effects"
                          >
                            <Check size={9} strokeWidth={3} /> AE
                          </span>
                        )}
                        {!isResolveImported && !isPremiereImported && !isAfterEffectsImported && (
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                            Choose target editor:
                          </span>
                        )}
                      </div>

                      {/* Right: Software Selection Dropdown + Nearby Import Button */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <select
                          className="input"
                          value={currentTarget}
                          onChange={(e) => handleEditorSelectionChange(job.id, e.target.value as EditorTarget)}
                          style={{
                            height: '28px',
                            padding: '2px 8px',
                            fontSize: '11px',
                            fontWeight: 800,
                            borderRadius: 'var(--radius-xs)',
                            border: '1.5px solid #000000',
                            backgroundColor: 'var(--bg-tertiary)',
                            color:
                              currentTarget === 'resolve'
                                ? 'var(--color-resolve)'
                                : currentTarget === 'premiere'
                                ? 'var(--color-premiere)'
                                : 'var(--color-ae)',
                            boxShadow: '1.5px 1.5px 0px #000000',
                            width: 'auto',
                            minWidth: '135px',
                            cursor: 'pointer',
                          }}
                          title="Select software for importing"
                        >
                          <option value="resolve">
                            DaVinci Resolve {isResolveImported ? '✓' : ''}
                          </option>
                          <option value="premiere">
                            Premiere Pro {isPremiereImported ? '✓' : ''}
                          </option>
                          <option value="aftereffects">
                            After Effects {isAfterEffectsImported ? '✓' : ''}
                          </option>
                        </select>

                        <button
                          onClick={() => handleTriggerImport(job.id, currentTarget)}
                          disabled={isCurrentlyImporting}
                          className={
                            currentTarget === 'aftereffects'
                              ? 'btn btn-sm btn-ae'
                              : currentTarget === 'premiere'
                              ? 'btn btn-sm btn-premiere'
                              : 'btn btn-sm btn-resolve'
                          }
                          style={{
                            height: '28px',
                            padding: '3px 10px',
                            fontSize: '11px',
                            fontWeight: 800,
                            gap: '4px',
                          }}
                          title={`Import asset into ${
                            currentTarget === 'resolve'
                              ? 'DaVinci Resolve'
                              : currentTarget === 'premiere'
                              ? 'Adobe Premiere Pro'
                              : 'Adobe After Effects'
                          }`}
                        >
                          {isCurrentlyImporting ? (
                            <span className="spin">⟳</span>
                          ) : (
                            <ArrowUpRight size={12} strokeWidth={2.5} />
                          )}
                          <span>
                            {isAlreadyImportedInTarget ? 'Re-import' : 'Import'}
                          </span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
