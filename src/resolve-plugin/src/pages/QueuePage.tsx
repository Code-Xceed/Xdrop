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
  importJobToAudition,
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
  GripVertical,
  Loader2,
  Download,
  Plus,
  Clock,
} from 'lucide-react';

interface QueuePageProps {
  downloads: DownloadJob[];
  onRefresh: () => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onSwitchToImport?: () => void;
}

type EditorTarget = 'resolve' | 'premiere' | 'aftereffects' | 'audition';

export const QueuePage: React.FC<QueuePageProps> = ({
  downloads,
  onRefresh,
  showToast,
  onSwitchToImport,
}) => {
  const { activeEditor } = useEditorContext();
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'failed'>('all');
  const [selectedEditorMap, setSelectedEditorMap] = useState<Record<string, EditorTarget>>({});
  const [importingId, setImportingId] = useState<string | null>(null);

  // Helper to determine target editor for a given job
  const getSelectedEditorForJob = (job: DownloadJob): EditorTarget => {
    if (selectedEditorMap[job.id]) {
      return selectedEditorMap[job.id];
    }
    if (
      activeEditor === 'premiere' ||
      activeEditor === 'aftereffects' ||
      activeEditor === 'audition' ||
      activeEditor === 'resolve'
    ) {
      return activeEditor;
    }
    const target = job.targetEditor || (job as any).target_editor;
    if (
      target === 'premiere' ||
      target === 'aftereffects' ||
      target === 'audition' ||
      target === 'resolve'
    ) {
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
      showToast('Download cancelled', 'info');
      onRefresh();
    } catch (e: any) {
      showToast(e.message || 'Failed to cancel', 'error');
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await retryDownload(id);
      showToast('Retrying download...', 'info');
      onRefresh();
    } catch (e: any) {
      showToast(e.message || 'Retry failed', 'error');
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await removeDownload(id);
      onRefresh();
    } catch (e: any) {
      showToast(e.message || 'Failed to remove', 'error');
    }
  };

  const handleTriggerImport = async (jobId: string, target: EditorTarget) => {
    setImportingId(jobId);
    try {
      if (target === 'premiere') {
        const res = await importJobToPremiere(jobId);
        if (res.success) {
          showToast('Imported into Premiere Pro bin', 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import into Premiere Pro', 'error');
        }
      } else if (target === 'aftereffects') {
        const res = await importJobToAfterEffects(jobId);
        if (res.success) {
          showToast('Imported into After Effects project', 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import into After Effects', 'error');
        }
      } else if (target === 'audition') {
        const res = await importJobToAudition(jobId);
        if (res.success) {
          showToast('Imported into Audition session', 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import into Audition', 'error');
        }
      } else {
        const res = await importJobToResolve(jobId);
        if (res.success) {
          showToast(`Imported into DaVinci Resolve: ${res.clipName || 'Media Pool'}`, 'success');
          onRefresh();
        } else {
          showToast(res.error || 'Failed to import into DaVinci Resolve', 'error');
        }
      }
    } catch (e: any) {
      showToast(e.message || 'Import error occurred', 'error');
    } finally {
      setImportingId(null);
    }
  };

  const activeDownloads = downloads.filter((j) =>
    ['downloading', 'processing', 'importing', 'queued'].includes(j.status)
  );
  const completedDownloads = downloads.filter((j) => j.status === 'completed');
  const failedDownloads = downloads.filter((j) => j.status === 'failed' || j.status === 'cancelled');

  const filteredJobs = downloads.filter((j) => {
    if (filter === 'active') return ['downloading', 'processing', 'importing', 'queued'].includes(j.status);
    if (filter === 'completed') return j.status === 'completed';
    if (filter === 'failed') return j.status === 'failed' || j.status === 'cancelled';
    return true;
  });

  // Empty State
  if (downloads.length === 0) {
    return (
      <div style={{ maxWidth: '480px', margin: '48px auto', padding: '0 16px', textAlign: 'center' }}>
        <div
          style={{
            padding: '36px 24px',
            borderRadius: 'var(--radius-lg)',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-default)',
            boxShadow: 'var(--shadow-sm)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-strong)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
              marginBottom: '14px',
            }}
          >
            <Download size={20} strokeWidth={1.8} />
          </div>
          <h4
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '6px',
              letterSpacing: '-0.01em',
            }}
          >
            No Downloads in Queue
          </h4>
          <p
            style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              lineHeight: 1.5,
              maxWidth: '320px',
              marginBottom: '18px',
            }}
          >
            Paste any YouTube, Instagram, TikTok, or web media link in the Import tab to begin downloading.
          </p>
          {onSwitchToImport && (
            <button
              onClick={onSwitchToImport}
              className="btn btn-primary btn-sm"
              style={{ padding: '6px 14px', fontSize: '11px', gap: '5px' }}
            >
              <Plus size={13} strokeWidth={2.2} />
              <span>Import Media</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 14px', maxWidth: '820px', margin: '0 auto' }}>
      {/* Segmented Filter Control Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
          gap: '8px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Transfers
          </span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              padding: '1px 6px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
            }}
          >
            {downloads.length}
          </span>
        </div>

        {/* Filter Pills */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            backgroundColor: 'var(--bg-secondary)',
            padding: '2px',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--border-default)',
            gap: '2px',
          }}
        >
          {(
            [
              { id: 'all', label: 'All', count: downloads.length },
              { id: 'active', label: 'Active', count: activeDownloads.length },
              { id: 'completed', label: 'Completed', count: completedDownloads.length },
              { id: 'failed', label: 'Errors', count: failedDownloads.length },
            ] as const
          ).map((item) => {
            const isSel = filter === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setFilter(item.id)}
                style={{
                  border: isSel ? '1px solid var(--border-strong)' : '1px solid transparent',
                  backgroundColor: isSel ? 'var(--bg-elevated)' : 'transparent',
                  color: isSel ? '#ffffff' : 'var(--text-muted)',
                  padding: '3px 9px',
                  borderRadius: 'var(--radius-pill)',
                  fontSize: '10px',
                  fontWeight: isSel ? 600 : 500,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 120ms ease',
                  boxShadow: isSel ? '0 1px 2px rgba(0,0,0,0.4)' : 'none',
                }}
              >
                <span>{item.label}</span>
                <span
                  style={{
                    fontSize: '9px',
                    fontFamily: 'var(--font-mono)',
                    opacity: isSel ? 1 : 0.7,
                  }}
                >
                  {item.count}
                </span>
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
          const isAuditionImported = Boolean(job.auditionImported ?? (job as any).audition_imported);

          const pendingImport = (
            [
              {
                editor: 'DaVinci Resolve',
                pending: Boolean(job.resolveImportPending ?? (job as any).resolve_import_pending),
                imported: isResolveImported,
                error: job.resolveImportError ?? (job as any).resolve_import_error ?? null,
              },
              {
                editor: 'Premiere Pro',
                pending: Boolean(job.premiereImportPending ?? (job as any).premiere_import_pending),
                imported: isPremiereImported,
                error: job.premiereImportError ?? (job as any).premiere_import_error ?? null,
              },
              {
                editor: 'After Effects',
                pending: Boolean(job.aftereffectsImportPending ?? (job as any).aftereffects_import_pending),
                imported: isAfterEffectsImported,
                error: job.aftereffectsImportError ?? (job as any).aftereffects_import_error ?? null,
              },
              {
                editor: 'Audition',
                pending: Boolean(job.auditionImportPending ?? (job as any).audition_import_pending),
                imported: isAuditionImported,
                error: job.auditionImportError ?? (job as any).audition_import_error ?? null,
              },
            ] as const
          ).find((state) => state.pending && !state.imported);

          const errorMsg = job.errorMessage || (job as any).error_message || 'Download failed';
          const formatStr = (job.format || 'MP4').toUpperCase();

          const wasAutoImportRequested = Boolean(job.autoImport ?? (job as any).auto_import);
          const targetEditor = (job.targetEditor ?? (job as any).target_editor) as EditorTarget | undefined;

          const isAutoImportedComplete =
            isCompleted &&
            wasAutoImportRequested &&
            ((targetEditor === 'resolve' && isResolveImported) ||
              (targetEditor === 'premiere' && isPremiereImported) ||
              (targetEditor === 'aftereffects' && isAfterEffectsImported) ||
              (targetEditor === 'audition' && isAuditionImported) ||
              (!targetEditor &&
                (isResolveImported || isPremiereImported || isAfterEffectsImported || isAuditionImported)));

          const currentTarget = getSelectedEditorForJob(job);
          const isCurrentlyImporting = importingId === job.id;

          const isAlreadyImportedInTarget =
            (currentTarget === 'resolve' && isResolveImported) ||
            (currentTarget === 'premiere' && isPremiereImported) ||
            (currentTarget === 'aftereffects' && isAfterEffectsImported) ||
            (currentTarget === 'audition' && isAuditionImported);

          const outputFilePath = job.outputFilePath || (job as any).output_file_path;
          const canDrag = isCompleted && Boolean(outputFilePath);

          // Status indicator color
          const statusAccentColor = isActive
            ? 'var(--accent-primary)'
            : isCompleted
            ? 'var(--success)'
            : isFailed
            ? 'var(--danger)'
            : 'var(--border-strong)';

          return (
            <div
              key={job.id}
              className="panel"
              draggable={canDrag}
              onDragStart={(e) => {
                if (canDrag && outputFilePath) {
                  e.dataTransfer.setData('text/plain', outputFilePath);
                  e.dataTransfer.setData('text/uri-list', `file:///${outputFilePath.replace(/\\/g, '/')}`);
                  e.dataTransfer.effectAllowed = 'copyMove';
                }
              }}
              style={{
                position: 'relative',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-xs)',
                cursor: canDrag ? 'grab' : 'default',
                transition: 'border-color 120ms ease, background 120ms ease',
              }}
              title={canDrag ? 'Drag clip directly onto timeline or bin' : undefined}
            >
              {/* Left Subtle Color Strip */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: '6px',
                  bottom: '6px',
                  width: '3px',
                  borderRadius: '0 2px 2px 0',
                  backgroundColor: statusAccentColor,
                  opacity: isActive ? 1 : 0.75,
                }}
              />

              {/* Row 1: Header (Grip / Media Icon / Title / Status Badge) */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '8px',
                  paddingLeft: '4px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                  {canDrag && (
                    <div
                      style={{
                        color: 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'grab',
                        flexShrink: 0,
                      }}
                      title="Drag to timeline"
                    >
                      <GripVertical size={13} strokeWidth={2} />
                    </div>
                  )}

                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-default)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--text-secondary)',
                      flexShrink: 0,
                    }}
                  >
                    {isAudio ? <Music size={12} strokeWidth={2} /> : <Film size={12} strokeWidth={2} />}
                  </div>

                  <h5
                    style={{
                      fontSize: '11.5px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      letterSpacing: '-0.01em',
                    }}
                    title={job.title || 'Untitled Asset'}
                  >
                    {job.title || 'Untitled Asset'}
                  </h5>
                </div>

                {/* Status Indicator Badge */}
                <div style={{ flexShrink: 0 }}>
                  {job.status === 'downloading' && (
                    <span
                      className="badge"
                      style={{
                        fontSize: '9px',
                        padding: '2px 7px',
                        gap: '4px',
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        color: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                      }}
                    >
                      <Loader2 size={10} className="spin" />
                      <span>{safeProgress.toFixed(0)}%</span>
                    </span>
                  )}
                  {job.status === 'processing' && (
                    <span
                      className="badge badge-warning"
                      style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}
                    >
                      <Loader2 size={10} className="spin" />
                      <span>Processing</span>
                    </span>
                  )}
                  {job.status === 'importing' && (
                    <span
                      className="badge"
                      style={{
                        fontSize: '9px',
                        padding: '2px 7px',
                        gap: '4px',
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        color: '#ffffff',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                      }}
                    >
                      <Loader2 size={10} className="spin" />
                      <span>Importing</span>
                    </span>
                  )}
                  {job.status === 'queued' && (
                    <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}>
                      <Clock size={9} strokeWidth={2} />
                      <span>Queued</span>
                    </span>
                  )}
                  {isCompleted && pendingImport && (
                    <span
                      className="badge badge-warning"
                      style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}
                      title={pendingImport.error || `Waiting for ${pendingImport.editor}`}
                    >
                      <Loader2 size={10} className="spin" />
                      <span>{pendingImport.editor} pending</span>
                    </span>
                  )}
                  {isCompleted && !pendingImport && (
                    <span
                      className="badge badge-success"
                      style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}
                    >
                      <CheckCircle2 size={10} strokeWidth={2.2} />
                      <span>Ready</span>
                    </span>
                  )}
                  {isFailed && (
                    <span
                      className="badge badge-danger"
                      style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}
                    >
                      <AlertCircle size={10} strokeWidth={2.2} />
                      <span>Failed</span>
                    </span>
                  )}
                  {isCancelled && (
                    <span
                      className="badge badge-neutral"
                      style={{ fontSize: '9px', padding: '2px 7px', gap: '4px' }}
                    >
                      <XCircle size={10} strokeWidth={2} />
                      <span>Cancelled</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Row 2: Sleek Precision Progress Bar */}
              <div
                style={{
                  width: '100%',
                  height: '3px',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  borderRadius: '2px',
                  overflow: 'hidden',
                  margin: '8px 0 6px',
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
                      : 'linear-gradient(90deg, rgba(255,255,255,0.7), #ffffff)',
                    transition: 'width 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                />
              </div>

              {/* Row 3: Monospace Telemetry & Quick Action Icons */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  gap: '8px',
                  paddingLeft: '4px',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    minWidth: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {job.status === 'downloading' ? (
                    <span>
                      {safeProgress.toFixed(0)}%
                      {totalBytes > 0
                        ? ` • ${formatBytes(downloadedBytes)} / ${formatBytes(totalBytes)}`
                        : downloadedBytes > 0
                        ? ` • ${formatBytes(downloadedBytes)}`
                        : ''}
                      {job.speed ? ` • ${job.speed}` : ''}
                      {job.eta ? ` • ETA ${job.eta}` : ''}
                    </span>
                  ) : job.status === 'processing' ? (
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Muxing audio and video streams...
                    </span>
                  ) : job.status === 'importing' ? (
                    <span style={{ color: '#ffffff' }}>
                      Registering clip into {targetEditor === 'premiere' ? 'Premiere Pro' : targetEditor === 'aftereffects' ? 'After Effects' : 'DaVinci Resolve'}...
                    </span>
                  ) : job.status === 'queued' ? (
                    <span>Awaiting download slot...</span>
                  ) : isCompleted ? (
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {formatStr} {job.qualityLabel ? `• ${job.qualityLabel}` : ''}
                      {downloadedBytes > 0 ? ` • ${formatBytes(downloadedBytes)}` : ''}
                    </span>
                  ) : isFailed ? (
                    <span style={{ color: 'var(--danger)' }}>{errorMsg}</span>
                  ) : (
                    <span>
                      {formatStr} {job.qualityLabel ? `• ${job.qualityLabel}` : ''}
                    </span>
                  )}
                </div>

                {/* Right Action Buttons */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                  {isActive && (
                    <button
                      onClick={() => handleCancel(job.id)}
                      className="btn btn-sm btn-danger"
                      style={{ padding: '2px 7px', fontSize: '10px' }}
                      title="Cancel download"
                    >
                      Cancel
                    </button>
                  )}

                  {(isFailed || isCancelled) && (
                    <button
                      onClick={() => handleRetry(job.id)}
                      className="btn btn-sm btn-secondary"
                      style={{ padding: '2px 7px', fontSize: '10px' }}
                      title="Retry download"
                    >
                      <RotateCcw size={10} strokeWidth={2} />
                      <span>Retry</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleRemove(job.id)}
                    className="btn btn-sm btn-ghost"
                    style={{ padding: '3px 5px' }}
                    title="Remove from queue"
                  >
                    <Trash2 size={12} strokeWidth={1.8} />
                  </button>
                </div>
              </div>

              {/* Row 4: Timeline / Bin Destination Bar */}
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
                    paddingLeft: '4px',
                  }}
                >
                  {isAutoImportedComplete ? (
                    /* Auto-imported mode: Clean confirmation pill */
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span
                        className="badge badge-success"
                        style={{
                          fontSize: '10px',
                          padding: '2px 8px',
                          fontWeight: 500,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <CheckCircle2 size={11} strokeWidth={2} />
                        <span>
                          Imported to{' '}
                          {targetEditor === 'aftereffects' || isAfterEffectsImported
                            ? 'After Effects'
                            : targetEditor === 'premiere' || isPremiereImported
                            ? 'Premiere Pro'
                            : 'DaVinci Resolve'}
                        </span>
                      </span>
                    </div>
                  ) : (
                    /* Manual import / Multi-editor selector */
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                        {isResolveImported && (
                          <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 5px' }}>
                            ✓ Resolve
                          </span>
                        )}
                        {isPremiereImported && (
                          <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 5px' }}>
                            ✓ Premiere
                          </span>
                        )}
                        {isAfterEffectsImported && (
                          <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 5px' }}>
                            ✓ AE
                          </span>
                        )}
                        {isAuditionImported && (
                          <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 5px' }}>
                            ✓ Audition
                          </span>
                        )}
                        {!isResolveImported &&
                          !isPremiereImported &&
                          !isAfterEffectsImported &&
                          !isAuditionImported && (
                            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                              Send to project:
                            </span>
                          )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <select
                          className="input"
                          value={currentTarget}
                          onChange={(e) => handleEditorSelectionChange(job.id, e.target.value as EditorTarget)}
                          style={{
                            height: '26px',
                            padding: '2px 8px',
                            fontSize: '10.5px',
                            fontWeight: 500,
                            borderRadius: 'var(--radius-xs)',
                            border: '1px solid var(--border-default)',
                            backgroundColor: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)',
                            boxShadow: 'none',
                            width: 'auto',
                            minWidth: '135px',
                            cursor: 'pointer',
                          }}
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
                          <option value="audition">
                            Audition {isAuditionImported ? '✓' : ''}
                          </option>
                        </select>

                        <button
                          onClick={() => handleTriggerImport(job.id, currentTarget)}
                          disabled={isCurrentlyImporting}
                          className="btn btn-sm btn-primary"
                          style={{
                            height: '26px',
                            padding: '2px 10px',
                            fontSize: '10.5px',
                            fontWeight: 600,
                            gap: '4px',
                          }}
                        >
                          {isCurrentlyImporting ? (
                            <Loader2 size={11} className="spin" />
                          ) : (
                            <ArrowUpRight size={11} strokeWidth={2.2} />
                          )}
                          <span>{isAlreadyImportedInTarget ? 'Re-import' : 'Import'}</span>
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
