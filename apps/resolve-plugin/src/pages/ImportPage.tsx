import React, { useState, useMemo } from 'react';
import { MediaInfo } from '@xdrop/shared-types';
import { analyzeUrl, createDownload } from '../services/api';
import { extractUrlsFromText, formatBytes, formatDuration } from '@xdrop/utilities';
import { useEditorContext } from '../context/EditorContext';
import { useTheme } from '../context/ThemeContext';
import {
  Search,
  Clipboard,
  X,
  Film,
  Music,
  Image as ImageIcon,
  CheckCircle,
  AlertTriangle,
  Download,
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  Radio,
} from 'lucide-react';

interface ImportPageProps {
  onJobStarted: () => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export interface PlatformDef {
  id: string;
  name: string;
  color: string;
  textColor: string;
  regex: RegExp;
  placeholder: string;
}

export const SUPPORTED_PLATFORMS: PlatformDef[] = [
  {
    id: 'youtube',
    name: 'YouTube',
    color: '#ff2a5f',
    textColor: '#ffffff',
    regex: /(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/|live\/)|youtu\.be\/)/i,
    placeholder: 'https://youtube.com/watch?v=...',
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    color: '#00f2fe',
    textColor: '#000000',
    regex: /(?:https?:\/\/)?(?:www\.|vm\.|vt\.)?tiktok\.com\//i,
    placeholder: 'https://tiktok.com/@creator/video/...',
  },
  {
    id: 'instagram',
    name: 'Instagram',
    color: '#ff2a8d',
    textColor: '#ffffff',
    regex: /(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/(?:reel|p|tv|stories|share)\//i,
    placeholder: 'https://instagram.com/reel/...',
  },
  {
    id: 'x',
    name: 'X (Twitter)',
    color: '#f8fafc',
    textColor: '#000000',
    regex: /(?:https?:\/\/)?(?:www\.)?(?:x\.com|twitter\.com|t\.co)\//i,
    placeholder: 'https://x.com/user/status/...',
  },
  {
    id: 'reddit',
    name: 'Reddit',
    color: '#ff4500',
    textColor: '#ffffff',
    regex: /(?:https?:\/\/)?(?:www\.|old\.)?(?:reddit\.com|v\.redd\.it|redd\.it)\//i,
    placeholder: 'https://reddit.com/r/videos/...',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    color: '#1877f2',
    textColor: '#ffffff',
    regex: /(?:https?:\/\/)?(?:www\.|m\.)?(?:facebook\.com|fb\.watch|fb\.com)\//i,
    placeholder: 'https://fb.watch/...',
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    color: '#e60023',
    textColor: '#ffffff',
    regex: /(?:https?:\/\/)?(?:www\.)?(?:pinterest\.(?:com|[a-z]{2,3})|pin\.it)\//i,
    placeholder: 'https://pin.it/...',
  },
  {
    id: 'vimeo',
    name: 'Vimeo',
    color: '#00b4d8',
    textColor: '#000000',
    regex: /(?:https?:\/\/)?(?:www\.)?(?:vimeo\.com|player\.vimeo\.com)\//i,
    placeholder: 'https://vimeo.com/...',
  },
  {
    id: 'direct',
    name: 'Direct Media',
    color: '#00ff88',
    textColor: '#000000',
    regex: /\.(mp4|mov|webm|m4v|mkv|mp3|wav|m4a|aac|flac|ogg|jpg|jpeg|png|webp|gif)(\?.*)?$/i,
    placeholder: 'https://.../video.mp4',
  },
];

export function detectPlatformFromUrl(inputUrl: string): PlatformDef | null {
  const trimmed = inputUrl.trim();
  if (!trimmed) return null;

  // 1. Direct media file extension check
  const direct = SUPPORTED_PLATFORMS.find((p) => p.id === 'direct');
  if (direct && direct.regex.test(trimmed)) {
    return direct;
  }

  // 2. Specific social media platform patterns
  for (const plat of SUPPORTED_PLATFORMS) {
    if (plat.id !== 'direct' && plat.regex.test(trimmed)) {
      return plat;
    }
  }

  // 3. Fallback domain string check
  const lower = trimmed.toLowerCase();
  for (const plat of SUPPORTED_PLATFORMS) {
    if (plat.id !== 'direct' && (lower.includes(plat.id) || (plat.id === 'x' && lower.includes('twitter')))) {
      return plat;
    }
  }

  return null;
}

export const ImportPage: React.FC<ImportPageProps> = ({
  onJobStarted,
  showToast,
}) => {
  const { activeEditor, activeEditorName, isEditorConnected } = useEditorContext();
  const { accentColor } = useTheme();

  const [urlInput, setUrlInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [mediaInfo, setMediaInfo] = useState<MediaInfo | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [targetBin, setTargetBin] = useState('Xdrop');
  const [autoImport, setAutoImport] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-detect platform dynamically as the user types or pastes
  const detectedPlatform = useMemo(() => {
    return detectPlatformFromUrl(urlInput);
  }, [urlInput]);

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrlInput(text.trim());
      }
    } catch (_) {
      showToast('Clipboard access was denied.', 'error');
    }
  };

  const handleClearInput = () => {
    setUrlInput('');
    setAnalysisError(null);
    setMediaInfo(null);
  };

  const handleSelectPlatformChip = (plat: PlatformDef) => {
    if (!urlInput.trim()) {
      setUrlInput(plat.placeholder);
    }
  };

  const handleAnalyze = async () => {
    const urls = extractUrlsFromText(urlInput);
    if (urls.length === 0) {
      setAnalysisError('Please enter a valid HTTP or HTTPS media URL.');
      return;
    }

    const targetUrl = urls[0];
    setIsAnalyzing(true);
    setAnalysisError(null);
    setMediaInfo(null);

    try {
      const info = await analyzeUrl(targetUrl);
      setMediaInfo(info);
      const defAsset = info.assets?.find((a) => a.isDefault) || info.assets?.[0];
      if (defAsset) {
        setSelectedAssetId(defAsset.id);
      }
    } catch (err: any) {
      setAnalysisError(err.message || 'Failed to inspect media from this URL.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !urlInput.includes('\n'))) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  const handleStartDownload = async (overrideEditor?: 'resolve' | 'premiere' | 'aftereffects') => {
    if (!mediaInfo) return;
    const assets = mediaInfo.assets || [];
    const asset = assets.find((a) => a.id === selectedAssetId) || assets[0];
    if (!asset) return;

    const editorToUse = overrideEditor || activeEditor;

    setIsSubmitting(true);
    try {
      await createDownload({
        source_url: mediaInfo.url,
        asset_id: asset.id,
        format: asset.format,
        quality_label: asset.qualityLabel,
        media_type: asset.mediaType,
        title: mediaInfo.title,
        author: mediaInfo.author || undefined,
        target_editor: editorToUse,
        target_media_pool_bin: targetBin,
        auto_import_to_resolve: editorToUse === 'resolve' ? autoImport : false,
        target_premiere_bin: targetBin,
        auto_import_to_premiere: editorToUse === 'premiere' ? autoImport : false,
        target_aftereffects_bin: targetBin,
        auto_import_to_aftereffects: editorToUse === 'aftereffects' ? autoImport : false,
        extract_audio_only: asset.mediaType === 'audio',
      });

      showToast(`Download started: ${mediaInfo.title}`, 'success');
      onJobStarted();
    } catch (err: any) {
      showToast(err.message || 'Failed to queue download.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedAsset = mediaInfo?.assets?.find((a) => a.id === selectedAssetId);

  return (
    <div style={{ padding: '12px 10px', maxWidth: '820px', margin: '0 auto' }}>
      {/* 1. Main Search & Import Bar Panel */}
      <div
        className="panel"
        style={{
          marginBottom: '12px',
          border: '1.5px solid #000000',
          boxShadow: 'var(--neo-shadow-card)',
          backgroundColor: 'var(--bg-secondary)',
          padding: '12px',
        }}
      >
        {/* Interactive URL Input */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              className="input"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste public video or media link..."
              style={{
                paddingLeft: '32px',
                paddingRight: urlInput ? '56px' : '32px',
                height: '38px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: 'var(--bg-primary)',
                borderColor: detectedPlatform ? detectedPlatform.color : 'var(--border-default)',
                boxShadow: detectedPlatform
                  ? `1.5px 1.5px 0px ${detectedPlatform.color}`
                  : 'var(--neo-shadow-xs)',
              }}
            />

            {/* Left Dynamic Platform Icon */}
            <div
              style={{
                position: 'absolute',
                left: '10px',
                top: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: detectedPlatform ? detectedPlatform.color : 'var(--text-muted)',
                transition: 'color 0.15s ease',
              }}
            >
              {detectedPlatform ? (
                <Radio size={15} strokeWidth={2.5} />
              ) : (
                <Search size={14} strokeWidth={2.5} />
              )}
            </div>

            {/* Right Action Icons: Clear & Paste */}
            <div
              style={{
                position: 'absolute',
                right: '6px',
                top: '7px',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
              }}
            >
              {urlInput && (
                <button
                  type="button"
                  onClick={handleClearInput}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title="Clear input"
                >
                  <X size={14} />
                </button>
              )}

              <button
                type="button"
                onClick={handlePasteClipboard}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                title="Paste from clipboard"
              >
                <Clipboard size={14} />
              </button>
            </div>
          </div>

          {/* Fetch CTA Button */}
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAnalyze}
            disabled={isAnalyzing || !urlInput.trim()}
            style={{
              height: '38px',
              padding: '0 14px',
              fontSize: '12px',
              fontWeight: 800,
              flexShrink: 0,
            }}
          >
            {isAnalyzing ? (
              <>
                <span className="spin">⟳</span>
                <span style={{ fontSize: '11px' }}>Inspecting...</span>
              </>
            ) : (
              <>
                <Sparkles size={13} strokeWidth={2.5} />
                <span>Fetch</span>
              </>
            )}
          </button>
        </div>

        {/* 2. Platform Detection Chips Strip */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            marginTop: '10px',
            flexWrap: 'wrap',
          }}
        >
          {SUPPORTED_PLATFORMS.map((plat) => {
            const isMatched = detectedPlatform?.id === plat.id;
            return (
              <button
                key={plat.id}
                type="button"
                onClick={() => handleSelectPlatformChip(plat)}
                style={{
                  fontSize: '9.5px',
                  fontWeight: 800,
                  padding: '2px 7px',
                  borderRadius: 'var(--radius-xs)',
                  border: isMatched ? '1.5px solid #000000' : '1px solid var(--border-subtle)',
                  backgroundColor: isMatched ? plat.color : 'var(--bg-tertiary)',
                  color: isMatched ? plat.textColor : 'var(--text-muted)',
                  boxShadow: isMatched ? '1.5px 1.5px 0px #000000' : 'none',
                  transform: isMatched ? 'translate(-0.5px, -0.5px)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.12s ease',
                  whiteSpace: 'nowrap',
                  lineHeight: '1.4',
                }}
                title={isMatched ? `${plat.name} link auto-detected` : `Supported: ${plat.name}`}
              >
                {plat.name}
              </button>
            );
          })}
        </div>

        {/* 3. Error Alert Notification */}
        {analysisError && (
          <div
            style={{
              marginTop: '10px',
              padding: '8px 10px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1.5px solid var(--color-resolve)',
              boxShadow: '2px 2px 0px var(--color-resolve)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              fontSize: '11px',
              color: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={14} strokeWidth={2.5} color="var(--color-resolve)" style={{ flexShrink: 0 }} />
              <span>{analysisError}</span>
            </div>
            <button
              onClick={() => setAnalysisError(null)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* 4. Inspected Asset Card */}
      {mediaInfo && (
        <div
          className="panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            backgroundColor: 'var(--bg-secondary)',
            border: '1.5px solid #000000',
            boxShadow: 'var(--neo-shadow-card)',
            padding: '14px',
          }}
        >
          {/* Media Header (Responsive Flex) */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {mediaInfo.thumbnailUrl ? (
              <div
                style={{
                  position: 'relative',
                  width: '120px',
                  height: '75px',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden',
                  backgroundColor: '#000000',
                  border: '1.5px solid #000000',
                  boxShadow: '2px 2px 0px #000000',
                  flexShrink: 0,
                }}
              >
                <img
                  src={mediaInfo.thumbnailUrl}
                  alt={mediaInfo.title}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                {mediaInfo.duration && (
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '3px',
                      right: '3px',
                      backgroundColor: 'rgba(0,0,0,0.85)',
                      color: '#ffffff',
                      fontSize: '9.5px',
                      fontWeight: 800,
                      padding: '1px 4px',
                      borderRadius: '2px',
                      border: '1px solid #ffffff',
                    }}
                  >
                    {formatDuration(mediaInfo.duration)}
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  width: '120px',
                  height: '75px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1.5px solid #000000',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                }}
              >
                <Film size={28} strokeWidth={2.5} />
              </div>
            )}

            <div style={{ flex: 1, minWidth: '180px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <span
                  className="badge"
                  style={{
                    backgroundColor: detectedPlatform ? detectedPlatform.color : '#ffffff',
                    color: detectedPlatform ? detectedPlatform.textColor : '#000000',
                  }}
                >
                  {(mediaInfo.platformName || mediaInfo.platform || 'MEDIA').toUpperCase()}
                </span>
                {mediaInfo.author && (
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {mediaInfo.author}
                  </span>
                )}
              </div>

              <h3
                style={{
                  fontSize: '13px',
                  fontWeight: 800,
                  lineHeight: 1.3,
                  color: '#ffffff',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
                title={mediaInfo.title}
              >
                {mediaInfo.title}
              </h3>
            </div>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-subtle)' }} />

          {/* Quality Grid (Responsive Tiles) */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, color: 'var(--text-secondary)' }}>
                SELECT QUALITY
              </span>
              <span style={{ fontSize: '10px', color: 'var(--success)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '3px' }}>
                <ShieldCheck size={11} strokeWidth={2.5} /> NLE Compatible (H.264 / AAC)
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '6px' }}>
              {(mediaInfo.assets || []).map((asset) => {
                const isSelected = selectedAssetId === asset.id;
                const isVideo = asset.mediaType === 'video';
                const isAudio = asset.mediaType === 'audio';

                return (
                  <div
                    key={asset.id}
                    onClick={() => setSelectedAssetId(asset.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      border: isSelected
                        ? '1.5px solid var(--accent-primary)'
                        : '1.5px solid var(--border-subtle)',
                      backgroundColor: isSelected
                        ? 'var(--accent-subtle)'
                        : 'var(--bg-tertiary)',
                      boxShadow: isSelected
                        ? '2px 2px 0px var(--accent-primary)'
                        : 'none',
                      cursor: 'pointer',
                      transition: 'all 0.08s ease',
                    }}
                  >
                    <div style={{ color: isSelected ? '#ffffff' : 'var(--text-muted)' }}>
                      {isVideo && <Film size={14} strokeWidth={2.5} />}
                      {isAudio && <Music size={14} strokeWidth={2.5} />}
                      {asset.mediaType === 'image' && <ImageIcon size={14} strokeWidth={2.5} />}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '11.5px', fontWeight: 800, color: isSelected ? '#ffffff' : 'var(--text-primary)' }}>
                        {asset.qualityLabel}
                      </div>
                      <div style={{ fontSize: '9.5px', color: 'var(--text-muted)' }}>
                        {(asset.format || 'MP4').toUpperCase()}
                        {asset.filesizeApprox ? ` • ${formatBytes(asset.filesizeApprox)}` : ''}
                      </div>
                    </div>

                    {isSelected && (
                      <CheckCircle
                        size={13}
                        strokeWidth={2.5}
                        color="var(--accent-primary)"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-subtle)' }} />

          {/* Destination & Action */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                Bin:
              </span>
              <input
                type="text"
                className="input"
                value={targetBin}
                onChange={(e) => setTargetBin(e.target.value)}
                placeholder="Xdrop"
                style={{ height: '32px', fontSize: '11px', flex: 1 }}
              />
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                <input
                  type="checkbox"
                  checked={autoImport}
                  onChange={(e) => setAutoImport(e.target.checked)}
                  style={{ accentColor: accentColor }}
                />
                <span style={{ color: 'var(--text-secondary)' }}>Auto-import</span>
              </label>
            </div>

            {/* Action Buttons: Primary + Quick Alternate Editor Imports */}
            <div style={{ display: 'flex', gap: '6px', width: '100%', alignItems: 'center' }}>
              {/* Secondary Alternate Buttons */}
              <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                {activeEditor !== 'resolve' && (
                  <button
                    type="button"
                    onClick={() => handleStartDownload('resolve')}
                    disabled={isSubmitting || !selectedAsset}
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '4px 7px', fontSize: '10px' }}
                    title="Import to DaVinci Resolve"
                  >
                    To Resolve
                  </button>
                )}
                {activeEditor !== 'premiere' && (
                  <button
                    type="button"
                    onClick={() => handleStartDownload('premiere')}
                    disabled={isSubmitting || !selectedAsset}
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '4px 7px', fontSize: '10px' }}
                    title="Import to Adobe Premiere Pro"
                  >
                    To Premiere
                  </button>
                )}
                {activeEditor !== 'aftereffects' && (
                  <button
                    type="button"
                    onClick={() => handleStartDownload('aftereffects')}
                    disabled={isSubmitting || !selectedAsset}
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '4px 7px', fontSize: '10px' }}
                    title="Import to Adobe After Effects"
                  >
                    To AE
                  </button>
                )}
              </div>

              {/* Primary Download CTA Button matching active editor theme */}
              <button
                type="button"
                className={
                  activeEditor === 'aftereffects'
                    ? 'btn btn-ae btn-lg'
                    : activeEditor === 'premiere'
                    ? 'btn btn-premiere btn-lg'
                    : 'btn btn-resolve btn-lg'
                }
                onClick={() => handleStartDownload()}
                disabled={isSubmitting || !selectedAsset}
                style={{ flex: 1, padding: '8px 14px', fontSize: '12px' }}
              >
                {activeEditor === 'aftereffects' ? (
                  <Sparkles size={14} strokeWidth={2.5} />
                ) : activeEditor === 'premiere' ? (
                  <Layers size={14} strokeWidth={2.5} />
                ) : (
                  <Download size={14} strokeWidth={2.5} />
                )}
                <span>
                  {autoImport && isEditorConnected
                    ? `Import to ${activeEditorName}`
                    : 'Download Asset'}
                </span>
                <ArrowRight size={13} strokeWidth={2.5} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
