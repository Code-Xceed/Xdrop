import React, { useState, useEffect } from 'react';
import { LibraryItem } from '@xdrop/shared-types';
import { formatBytes, formatDuration } from '@xdrop/utilities';
import { useEditorContext } from '../context/EditorContext';
import {
  getLibrary,
  deleteLibraryItem,
  importLibraryItem,
  importLibraryItemToPremiere,
  importLibraryItemToAfterEffects,
  revealLibraryItem,
} from '../services/api';
import {
  Search,
  Film,
  Music,
  Folder,
  Trash2,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';

interface LibraryPageProps {
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  isActive?: boolean;
}

type EditorTarget = 'resolve' | 'premiere' | 'aftereffects';

export const LibraryPage: React.FC<LibraryPageProps> = ({ showToast, isActive }) => {
  const { activeEditor } = useEditorContext();
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [mediaTypeFilter, setMediaTypeFilter] = useState('');
  const [selectedEditorMap, setSelectedEditorMap] = useState<Record<string, EditorTarget>>({});
  const [importingId, setImportingId] = useState<string | null>(null);

  const getSelectedEditorForAsset = (assetId: string): EditorTarget => {
    if (selectedEditorMap[assetId]) {
      return selectedEditorMap[assetId];
    }
    if (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'resolve') {
      return activeEditor;
    }
    return 'resolve';
  };

  const handleEditorSelectionChange = (assetId: string, editor: EditorTarget) => {
    setSelectedEditorMap((prev) => ({
      ...prev,
      [assetId]: editor,
    }));
  };

  const fetchAssets = async (silent = false) => {
    if (!silent && items.length === 0) {
      setIsLoading(true);
    }
    try {
      const data = await getLibrary({
        search: search || undefined,
        platform: platformFilter || undefined,
        mediaType: (mediaTypeFilter as any) || undefined,
      });
      setItems(data.items);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isActive !== false) {
      fetchAssets(items.length > 0);
    }
  }, [isActive, platformFilter, mediaTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAssets();
  };

  const handleTriggerImport = async (id: string, target: EditorTarget) => {
    setImportingId(id);
    try {
      if (target === 'premiere') {
        const res = await importLibraryItemToPremiere(id);
        if (res.success) {
          showToast('Imported into Adobe Premiere Pro project bin!', 'success');
          fetchAssets();
        } else {
          showToast(res.error || 'Failed to import to Premiere Pro. Ensure Premiere is open.', 'error');
        }
      } else if (target === 'aftereffects') {
        const res = await importLibraryItemToAfterEffects(id);
        if (res.success) {
          showToast('Imported into Adobe After Effects project panel!', 'success');
          fetchAssets();
        } else {
          showToast(res.error || 'Failed to import to After Effects. Ensure AE is open.', 'error');
        }
      } else {
        const res = await importLibraryItem(id);
        if (res.success) {
          showToast(`Imported into DaVinci Resolve: ${res.clipName || 'Clip'}`, 'success');
          fetchAssets();
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

  const handleReveal = async (id: string) => {
    try {
      await revealLibraryItem(id);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleDelete = async (id: string) => {
    const deletePhysical = window.confirm(
      'Remove from Library?\nClick OK to also remove the file from your hard drive, or Cancel to remove from library catalog only.'
    );
    try {
      await deleteLibraryItem(id, deletePhysical);
      showToast('Asset removed.', 'info');
      fetchAssets();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '12px 10px' }}>
      {/* Search and Filters Bar */}
      <div
        className="panel"
        style={{
          marginBottom: '12px',
          padding: '10px 12px',
          backgroundColor: 'var(--bg-secondary)',
          border: '1.5px solid #000000',
          boxShadow: 'var(--neo-shadow-card)',
        }}
      >
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1 1 180px', minWidth: 0 }}>
            <input
              type="text"
              className="input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search library..."
              style={{
                paddingLeft: '32px',
                height: '34px',
                fontSize: '11.5px',
                backgroundColor: 'var(--bg-primary)',
              }}
            />
            <Search
              size={14}
              strokeWidth={2.5}
              style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '6px', flex: '1 1 auto', minWidth: 0 }}>
            <select
              className="input"
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              style={{ flex: 1, minWidth: '95px', height: '34px', fontSize: '11px', backgroundColor: 'var(--bg-primary)' }}
            >
              <option value="">All Platforms</option>
              <option value="youtube">YouTube</option>
              <option value="tiktok">TikTok</option>
              <option value="instagram">Instagram</option>
              <option value="x">X / Twitter</option>
              <option value="reddit">Reddit</option>
              <option value="facebook">Facebook</option>
              <option value="pinterest">Pinterest</option>
              <option value="vimeo">Vimeo</option>
              <option value="direct">Direct File</option>
            </select>

            <select
              className="input"
              value={mediaTypeFilter}
              onChange={(e) => setMediaTypeFilter(e.target.value)}
              style={{ flex: 1, minWidth: '85px', height: '34px', fontSize: '11px', backgroundColor: 'var(--bg-primary)' }}
            >
              <option value="">All Types</option>
              <option value="video">Videos</option>
              <option value="audio">Audios</option>
              <option value="image">Images</option>
            </select>
          </div>
        </form>
      </div>

      {/* Asset Grid */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px 16px', color: 'var(--text-muted)' }}>
          <span className="spin" style={{ display: 'inline-block', fontSize: '20px', marginBottom: '6px' }}>⟳</span>
          <p style={{ fontSize: '11.5px', fontWeight: 800 }}>LOADING LIBRARY...</p>
        </div>
      ) : items.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '40px 16px',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-sm)',
            border: '1.5px solid #000000',
            boxShadow: 'var(--neo-shadow-card)',
          }}
        >
          <Folder size={32} strokeWidth={2.5} style={{ color: 'var(--text-muted)', marginBottom: '8px' }} />
          <h4 style={{ fontSize: '13px', fontWeight: 800, marginBottom: '4px', color: '#ffffff' }}>
            No Media Assets Indexed
          </h4>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', maxWidth: '360px', margin: '0 auto' }}>
            Downloaded files appear here for 1-click re-importing into Resolve, Premiere, or After Effects.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '10px' }}>
          {items.map((asset) => {
            const currentTarget = getSelectedEditorForAsset(asset.id);
            const isImporting = importingId === asset.id;

            return (
              <div
                key={asset.id}
                className="panel"
                style={{
                  padding: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1.5px solid #000000',
                  boxShadow: '2px 2px 0px #000000',
                }}
              >
                {/* Thumbnail Area */}
                <div
                  style={{
                    position: 'relative',
                    width: '100%',
                    height: '115px',
                    backgroundColor: '#000000',
                    borderRadius: 'var(--radius-xs)',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid #000000',
                  }}
                >
                  {asset.thumbnailPath ? (
                    <img
                      src={`/thumbnails/${asset.thumbnailPath.split(/[/\\]/).pop()}`}
                      alt={asset.title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <div style={{ color: 'var(--text-muted)' }}>
                      {asset.mediaType === 'audio' ? <Music size={32} strokeWidth={2} /> : <Film size={32} strokeWidth={2} />}
                    </div>
                  )}

                  {/* Duration Badge */}
                  {asset.duration && (
                    <div
                      style={{
                        position: 'absolute',
                        bottom: '4px',
                        right: '4px',
                        backgroundColor: 'rgba(0,0,0,0.85)',
                        color: '#ffffff',
                        fontSize: '9px',
                        fontWeight: 800,
                        padding: '1px 4px',
                        borderRadius: '2px',
                        border: '1px solid rgba(255,255,255,0.4)',
                      }}
                    >
                      {formatDuration(asset.duration)}
                    </div>
                  )}

                  {/* Platform Tag */}
                  <div style={{ position: 'absolute', top: '4px', left: '4px' }}>
                    <span
                      className="badge"
                      style={{
                        fontSize: '8.5px',
                        backgroundColor: '#ffffff',
                        color: '#000000',
                        padding: '1px 4px',
                      }}
                    >
                      {(asset.platform || 'MEDIA').toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Title & Metadata */}
                <div>
                  <h4
                    style={{
                      fontSize: '12px',
                      fontWeight: 800,
                      color: '#ffffff',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      marginBottom: '2px',
                    }}
                    title={asset.title || 'Untitled Asset'}
                  >
                    {asset.title || 'Untitled Asset'}
                  </h4>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9.5px', color: 'var(--text-muted)' }}>
                    <span style={{ fontWeight: 800, color: 'var(--text-secondary)' }}>
                      {(asset.format || 'MP4').toUpperCase()}
                    </span>
                    {asset.resolution && <span>• {asset.resolution}</span>}
                    <span>• {formatBytes(asset.fileSizeBytes ?? (asset as any).file_size_bytes ?? 0)}</span>
                    <span style={{ marginLeft: 'auto', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 800 }}>
                      <ShieldCheck size={11} strokeWidth={2.5} /> NLE
                    </span>
                  </div>
                </div>

                {/* Action Area: Dropdown for Editor Target + Import Button + Reveal/Delete */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: 'auto',
                    paddingTop: '8px',
                    borderTop: '1px solid var(--border-subtle)',
                    gap: '4px',
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap', flex: 1, minWidth: 0 }}>
                    <select
                      className="input"
                      value={currentTarget}
                      onChange={(e) => handleEditorSelectionChange(asset.id, e.target.value as EditorTarget)}
                      style={{
                        height: '26px',
                        padding: '1px 6px',
                        fontSize: '10px',
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
                        boxShadow: '1px 1px 0px #000000',
                        width: 'auto',
                        minWidth: '95px',
                        flex: '1 1 auto',
                        cursor: 'pointer',
                      }}
                      title="Select software for import"
                    >
                      <option value="resolve">DaVinci Resolve</option>
                      <option value="premiere">Premiere Pro</option>
                      <option value="aftereffects">After Effects</option>
                    </select>

                    <button
                      onClick={() => handleTriggerImport(asset.id, currentTarget)}
                      disabled={isImporting}
                      className={
                        currentTarget === 'aftereffects'
                          ? 'btn btn-sm btn-ae'
                          : currentTarget === 'premiere'
                          ? 'btn btn-sm btn-premiere'
                          : 'btn btn-sm btn-resolve'
                      }
                      style={{ padding: '2px 7px', fontSize: '10px', height: '26px' }}
                      title={`Import to ${
                        currentTarget === 'resolve'
                          ? 'DaVinci Resolve'
                          : currentTarget === 'premiere'
                          ? 'Premiere Pro'
                          : 'After Effects'
                      }`}
                    >
                      {isImporting ? (
                        <span className="spin">⟳</span>
                      ) : (
                        <ArrowUpRight size={10} strokeWidth={2.5} />
                      )}
                      <span>Import</span>
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: '2px', flexShrink: 0 }}>
                    <button
                      onClick={() => handleReveal(asset.id)}
                      className="btn btn-sm btn-ghost"
                      style={{ padding: '3px 4px' }}
                      title="Reveal in Explorer"
                    >
                      <Folder size={12} strokeWidth={2.5} />
                    </button>

                    <button
                      onClick={() => handleDelete(asset.id)}
                      className="btn btn-sm btn-ghost"
                      style={{ padding: '3px 4px', color: 'var(--color-resolve)' }}
                      title="Delete asset"
                    >
                      <Trash2 size={12} strokeWidth={2.5} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
