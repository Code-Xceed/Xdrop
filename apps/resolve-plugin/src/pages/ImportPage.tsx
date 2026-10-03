import React, { useState, useMemo, useEffect } from 'react';
import { MediaInfo } from '@xdrop/shared-types';
import { analyzeUrl, createDownload } from '../services/api';
import { extractUrlsFromText, formatBytes, formatDuration } from '@xdrop/utilities';
import { useEditorContext } from '../context/EditorContext';
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
  SlidersHorizontal,
  Zap,
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
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.|music\.)?youtube\.com\/(?:watch\?|shorts\/|embed\/|live\/|v\/|clip\/)|youtu\.be\/)/i,
    placeholder: 'https://youtube.com/watch?v=...',
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|vm\.|vt\.|m\.)?tiktok\.com\/)/i,
    placeholder: 'https://tiktok.com/@creator/video/...',
  },
  {
    id: 'instagram',
    name: 'Instagram',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.)?instagram\.com|instagr\.am)\/(?:reel|reels|p|tv|stories|share)\//i,
    placeholder: 'https://instagram.com/reel/...',
  },
  {
    id: 'x',
    name: 'X (Twitter)',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|mobile\.)?(?:twitter\.com|x\.com)\/(?:[^/]+\/status\/\d+|i\/status\/\d+)|t\.co\/[a-zA-Z0-9]+)/i,
    placeholder: 'https://x.com/user/status/...',
  },
  {
    id: 'reddit',
    name: 'Reddit',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|old\.|new\.|m\.)?reddit\.com\/(?:r\/[^/]+\/(?:comments|s)\/|clip\/)|v\.redd\.it\/[a-zA-Z0-9]+|redd\.it\/[a-zA-Z0-9]+)/i,
    placeholder: 'https://reddit.com/r/videos/...',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.|fb\.)?facebook\.com\/(?:watch\/?\?|reel\/|reels\/|share\/[rv]\/|[^/]+\/videos\/)|fb\.watch\/[a-zA-Z0-9_\-]+)/i,
    placeholder: 'https://fb.watch/...',
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.)?pinterest\.(?:com|[a-z]{2,3}(?:\.[a-z]{2})?)\/pin\/|pin\.it\/[a-zA-Z0-9]+)/i,
    placeholder: 'https://pin.it/...',
  },
  {
    id: 'vimeo',
    name: 'Vimeo',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /(?:https?:\/\/)?(?:(?:www\.|player\.)?vimeo\.com\/(?:channels\/[^/]+\/|groups\/[^/]+\/videos\/|showcase\/[^/]+\/video\/|manage\/videos\/|video\/)?\d+)/i,
    placeholder: 'https://vimeo.com/...',
  },
  {
    id: 'direct',
    name: 'Direct Media',
    color: '#f4f4f5',
    textColor: '#090a0c',
    regex: /\.(mp4|mov|webm|m4v|mkv|avi|flv|mp3|wav|m4a|aac|flac|ogg|aiff|wma|jpg|jpeg|png|webp|gif)(\?.*)?$/i,
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
  const { activeEditor } = useEditorContext();

  const [urlInput, setUrlInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [mediaInfo, setMediaInfo] = useState<MediaInfo | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [targetBin, setTargetBin] = useState('Xdrop');
  const [autoImport, setAutoImport] = useState(true);
  const [autoImportEditor, setAutoImportEditor] = useState<'resolve' | 'premiere' | 'aftereffects'>(() => {
    if (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'resolve') {
      return activeEditor;
    }
    return 'resolve';
  });
  const [userSelectedEditor, setUserSelectedEditor] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Quality mode: 'presets' vs 'custom'
  const [qualityMode, setQualityMode] = useState<'presets' | 'custom'>('presets');
  const [presetCategory, setPresetCategory] = useState<'all' | 'video' | 'audio' | 'image'>('all');

  // Custom selection dropdown state
  const [customMediaType, setCustomMediaType] = useState<'video' | 'audio' | 'image'>('video');
  const [customQualityAssetId, setCustomQualityAssetId] = useState<string>('');
  const [customFormat, setCustomFormat] = useState<string>('mp4');

  // Categorized asset collections
  const videoAssets = useMemo(() => {
    return (mediaInfo?.assets || []).filter((a) => {
      const mt = a.mediaType || (a as any).media_type || 'video';
      return mt === 'video';
    });
  }, [mediaInfo]);

  const audioAssets = useMemo(() => {
    return (mediaInfo?.assets || []).filter((a) => {
      const mt = a.mediaType || (a as any).media_type;
      return mt === 'audio';
    });
  }, [mediaInfo]);

  const imageAssets = useMemo(() => {
    return (mediaInfo?.assets || []).filter((a) => {
      const mt = a.mediaType || (a as any).media_type;
      return mt === 'image';
    });
  }, [mediaInfo]);

  const filteredPresetAssets = useMemo(() => {
    const assets = mediaInfo?.assets || [];
    if (presetCategory === 'all') return assets;
    return assets.filter((a) => {
      const mt = a.mediaType || (a as any).media_type;
      return mt === presetCategory;
    });
  }, [mediaInfo, presetCategory]);

  const handleCustomMediaTypeChange = (newType: 'video' | 'audio' | 'image') => {
    setCustomMediaType(newType);
    if (!mediaInfo) return;
    const assets = mediaInfo.assets || [];
    if (newType === 'video') {
      const vid = assets.find((a) => (a.mediaType || (a as any).media_type) === 'video');
      if (vid) setCustomQualityAssetId(vid.id);
      setCustomFormat('mp4');
    } else if (newType === 'audio') {
      const aud = assets.find((a) => (a.mediaType || (a as any).media_type) === 'audio');
      if (aud) setCustomQualityAssetId(aud.id);
      setCustomFormat('wav');
    } else {
      const img = assets.find((a) => (a.mediaType || (a as any).media_type) === 'image');
      if (img) setCustomQualityAssetId(img.id);
      setCustomFormat('jpg');
    }
  };

  // Synchronize autoImportEditor with activeEditor if user hasn't manually selected one
  useEffect(() => {
    if (!userSelectedEditor && (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'resolve')) {
      setAutoImportEditor(activeEditor);
    }
  }, [activeEditor, userSelectedEditor]);

  // Thumbnail state with resilient proxy fallback
  const [thumbSrc, setThumbSrc] = useState<string | null>(null);
  const [thumbError, setThumbError] = useState(false);

  useEffect(() => {
    const rawThumb = mediaInfo?.thumbnailUrl || (mediaInfo as any)?.thumbnail_url;
    if (rawThumb) {
      setThumbSrc(rawThumb);
      setThumbError(false);
    } else {
      setThumbSrc(null);
      setThumbError(false);
    }
  }, [mediaInfo]);

  const handleThumbError = () => {
    const rawThumb = mediaInfo?.thumbnailUrl || (mediaInfo as any)?.thumbnail_url;
    if (!rawThumb) return;
    const proxyUrl = `/api/analyze/thumbnail-proxy?url=${encodeURIComponent(rawThumb)}`;
    if (thumbSrc !== proxyUrl) {
      // Retry via local proxy endpoint to bypass any CDN referer or CORS blocks
      setThumbSrc(proxyUrl);
    } else {
      // Both direct and proxy failed
      setThumbError(true);
    }
  };

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
      const defAsset = (info.assets || []).find((a) => a.isDefault || (a as any).is_default) || info.assets?.[0];
      if (defAsset) {
        setSelectedAssetId(defAsset.id);
        const mType = ((defAsset.mediaType || (defAsset as any).media_type || 'video') as 'video' | 'audio' | 'image');
        setCustomMediaType(mType);
        setCustomQualityAssetId(defAsset.id);
        setCustomFormat(defAsset.format || (mType === 'audio' ? 'wav' : 'mp4'));
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
    const editorToUse = overrideEditor || (autoImport ? autoImportEditor : 'none');

    let assetId = selectedAssetId;
    let format = 'mp4';
    let qualityLabel = 'Standard';
    let mediaType = 'video';
    let transcodeVfmt: string | undefined = undefined;
    let transcodeAfmt: string | undefined = undefined;
    let extractAudioOnly = false;

    if (qualityMode === 'custom') {
      mediaType = customMediaType;
      format = customFormat;
      extractAudioOnly = customMediaType === 'audio';

      if (customMediaType === 'video') {
        assetId = customQualityAssetId || 'best_video';
        const matched = (mediaInfo.assets || []).find((a) => a.id === assetId);
        qualityLabel = matched ? (matched.qualityLabel || (matched as any).quality_label || 'Custom Video') : 'Custom Video';
        if (customFormat === 'mov') {
          transcodeVfmt = 'mov';
        } else if (customFormat === 'mp4') {
          transcodeVfmt = 'mp4';
        }
      } else if (customMediaType === 'audio') {
        assetId = customQualityAssetId || 'audio_wav';
        qualityLabel = `Custom Audio (${customFormat.toUpperCase()})`;
        transcodeAfmt = customFormat;
      } else {
        assetId = 'thumbnail_image';
        qualityLabel = 'Custom Image';
      }
    } else {
      const assets = mediaInfo.assets || [];
      const asset = assets.find((a) => a.id === selectedAssetId) || assets[0];
      if (!asset) return;

      assetId = asset.id;
      format = asset.format;
      qualityLabel = asset.qualityLabel || (asset as any).quality_label || (asset.format || 'MP4').toUpperCase();
      mediaType = asset.mediaType || (asset as any).media_type || 'video';
      extractAudioOnly = mediaType === 'audio';
      if (asset.format === 'mov' || asset.id.includes('prores')) {
        transcodeVfmt = 'mov';
      }
    }

    setIsSubmitting(true);
    try {
      await createDownload({
        source_url: mediaInfo.url,
        asset_id: assetId,
        format: format,
        quality_label: qualityLabel,
        media_type: mediaType,
        title: mediaInfo.title,
        author: mediaInfo.author || undefined,
        target_editor: editorToUse,
        target_media_pool_bin: targetBin,
        auto_import_to_resolve: autoImport && editorToUse === 'resolve',
        target_premiere_bin: targetBin,
        auto_import_to_premiere: autoImport && editorToUse === 'premiere',
        target_aftereffects_bin: targetBin,
        auto_import_to_aftereffects: autoImport && editorToUse === 'aftereffects',
        transcode_video_format: transcodeVfmt,
        transcode_audio_format: transcodeAfmt,
        extract_audio_only: extractAudioOnly,
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
          border: '1px solid var(--border-default)',
          boxShadow: 'var(--shadow-sm)',
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
                height: '36px',
                fontSize: '11.5px',
                fontWeight: 500,
                backgroundColor: 'var(--bg-primary)',
                borderColor: detectedPlatform ? 'rgba(255, 255, 255, 0.35)' : 'var(--border-default)',
                boxShadow: 'none',
              }}
            />

            {/* Left Dynamic Platform Icon */}
            <div
              style={{
                position: 'absolute',
                left: '10px',
                top: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: detectedPlatform ? 'var(--text-primary)' : 'var(--text-muted)',
                transition: 'color 0.15s ease',
              }}
            >
              {detectedPlatform ? (
                <Radio size={14} strokeWidth={2} />
              ) : (
                <Search size={14} strokeWidth={2} />
              )}
            </div>

            {/* Right Action Icons: Clear & Paste */}
            <div
              style={{
                position: 'absolute',
                right: '6px',
                top: '6px',
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
                  <X size={13} />
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
                <Clipboard size={13} />
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
              height: '36px',
              padding: '0 14px',
              fontSize: '11.5px',
              fontWeight: 600,
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
                <Sparkles size={12} strokeWidth={2} />
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
            gap: '4px',
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
                  fontWeight: isMatched ? 600 : 500,
                  padding: '2px 7px',
                  borderRadius: 'var(--radius-xs)',
                  border: isMatched ? '1px solid rgba(255, 255, 255, 0.35)' : '1px solid var(--border-subtle)',
                  backgroundColor: isMatched ? 'rgba(255, 255, 255, 0.12)' : 'var(--bg-tertiary)',
                  color: isMatched ? '#ffffff' : 'var(--text-muted)',
                  boxShadow: 'none',
                  transform: 'none',
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

        {/* 3. Analyzing / Inspecting State Notification */}
        {isAnalyzing && (
          <div
            style={{
              marginTop: '10px',
              padding: '12px 14px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <div className="spin" style={{ color: 'var(--text-secondary)', fontSize: '16px', flexShrink: 0 }}>⟳</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Analyzing Media Streams & Quality Presets...
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Probing video codecs, audio sample rates, resolutions, and direct platform stream links
              </div>
            </div>
            <span
              style={{
                fontSize: '9px',
                fontWeight: 600,
                color: '#ffffff',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.18)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-xs)',
                whiteSpace: 'nowrap',
              }}
            >
              PROBE ACTIVE
            </span>
          </div>
        )}

        {/* 4. Error Alert Notification */}
        {analysisError && (
          <div
            style={{
              marginTop: '10px',
              padding: '8px 12px',
              backgroundColor: 'var(--danger-subtle)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              fontSize: '11px',
              color: '#f87171',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={14} strokeWidth={2} color="#f87171" style={{ flexShrink: 0 }} />
              <span>{analysisError}</span>
            </div>
            <button
              onClick={() => setAnalysisError(null)}
              style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', padding: '2px' }}
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
            border: '1px solid var(--border-default)',
            boxShadow: 'var(--shadow-sm)',
            padding: '14px',
          }}
        >
          {/* Media Header (Responsive Flex) */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {thumbSrc && !thumbError ? (
              <div
                style={{
                  position: 'relative',
                  width: '125px',
                  height: '78px',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden',
                  backgroundColor: '#000000',
                  border: '1px solid var(--border-default)',
                  flexShrink: 0,
                }}
              >
                <img
                  src={thumbSrc}
                  alt={mediaInfo.title}
                  referrerPolicy="no-referrer"
                  crossOrigin="anonymous"
                  onError={handleThumbError}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
                {mediaInfo.duration && (
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '3px',
                      right: '3px',
                      backgroundColor: 'rgba(0,0,0,0.8)',
                      color: '#ffffff',
                      fontSize: '9px',
                      fontWeight: 600,
                      padding: '1px 4px',
                      borderRadius: '2px',
                    }}
                  >
                    {formatDuration(mediaInfo.duration)}
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  width: '125px',
                  height: '78px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                  gap: '4px',
                  flexShrink: 0,
                }}
              >
                <Film size={22} strokeWidth={2} />
                <span style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)' }}>
                  {(mediaInfo.platform || 'MEDIA').toUpperCase()}
                </span>
              </div>
            )}

            <div style={{ flex: 1, minWidth: '180px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <span
                  className="badge badge-neutral"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    color: '#ffffff',
                    border: '1px solid rgba(255, 255, 255, 0.16)',
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

          {/* Quality Mode Switcher & Selector */}
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
                marginBottom: '10px',
              }}
            >
              {/* Segmented Control: Presets vs Custom */}
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-default)',
                  gap: '2px',
                }}
              >
                <button
                  type="button"
                  onClick={() => setQualityMode('presets')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: qualityMode === 'presets' ? 600 : 500,
                    borderRadius: 'var(--radius-xs)',
                    border: 'none',
                    backgroundColor: qualityMode === 'presets' ? 'var(--accent-primary)' : 'transparent',
                    color: qualityMode === 'presets' ? 'var(--accent-text)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.1s ease',
                  }}
                >
                  <Zap size={12} strokeWidth={2} />
                  <span>Presets ({mediaInfo.assets?.length || 0})</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setQualityMode('custom');
                    if (!customQualityAssetId && mediaInfo.assets && mediaInfo.assets.length > 0) {
                      setCustomQualityAssetId(mediaInfo.assets[0].id);
                    }
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: qualityMode === 'custom' ? 600 : 500,
                    borderRadius: 'var(--radius-xs)',
                    border: 'none',
                    backgroundColor: qualityMode === 'custom' ? 'var(--accent-primary)' : 'transparent',
                    color: qualityMode === 'custom' ? 'var(--accent-text)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.1s ease',
                  }}
                >
                  <SlidersHorizontal size={12} strokeWidth={2} />
                  <span>Custom Settings</span>
                </button>
              </div>

              {/* Status / NLE Badge */}
              <span
                style={{
                  fontSize: '9.5px',
                  color: 'var(--text-secondary)',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  padding: '3px 7px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <ShieldCheck size={11} strokeWidth={2} /> NLE Compatible (H.264 / AAC / ProRes)
              </span>
            </div>

            {/* TAB 1: PRESETS MODE */}
            {qualityMode === 'presets' && (
              <div>
                {/* Category Filter Pills (All, Video, Audio, Image) */}
                <div style={{ display: 'flex', gap: '5px', marginBottom: '8px', flexWrap: 'wrap' }}>
                  {[
                    { id: 'all', label: 'All', count: mediaInfo.assets?.length || 0 },
                    { id: 'video', label: 'Video', count: videoAssets.length },
                    { id: 'audio', label: 'Audio Only', count: audioAssets.length },
                    ...(imageAssets.length > 0
                      ? [{ id: 'image', label: 'Artwork / Cover', count: imageAssets.length }]
                      : []),
                  ].map((cat) => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setPresetCategory(cat.id as any)}
                      style={{
                        padding: '3px 8px',
                        fontSize: '10px',
                        fontWeight: presetCategory === cat.id ? 600 : 500,
                        borderRadius: 'var(--radius-xs)',
                        border: presetCategory === cat.id
                          ? '1px solid rgba(255, 255, 255, 0.35)'
                          : '1px solid var(--border-subtle)',
                        backgroundColor: presetCategory === cat.id
                          ? 'rgba(255, 255, 255, 0.1)'
                          : 'var(--bg-tertiary)',
                        color: presetCategory === cat.id ? '#ffffff' : 'var(--text-muted)',
                        cursor: 'pointer',
                        transition: 'all 0.12s ease',
                      }}
                    >
                      {cat.label} ({cat.count})
                    </button>
                  ))}
                </div>

                {/* Preset Cards Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '6px' }}>
                  {filteredPresetAssets.map((asset) => {
                    const isSelected = selectedAssetId === asset.id;
                    const mType = asset.mediaType || (asset as any).media_type || 'video';
                    const isVideo = mType === 'video';
                    const isAudio = mType === 'audio';
                    const isImage = mType === 'image';
                    const qLabel = asset.qualityLabel || (asset as any).quality_label || (asset.format ? asset.format.toUpperCase() : 'Best');
                    const fSize = asset.filesizeApprox ?? (asset as any).filesize_approx;
                    const fmtUpper = (asset.format || 'MP4').toUpperCase();
                    const isProRes = asset.id.includes('prores') || (asset.format === 'mov' && isVideo);

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
                            ? '1px solid #ffffff'
                            : '1px solid var(--border-default)',
                          backgroundColor: isSelected
                            ? 'rgba(255, 255, 255, 0.08)'
                            : 'var(--bg-tertiary)',
                          boxShadow: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.12s ease',
                          minHeight: '44px',
                        }}
                      >
                        <div style={{ color: isSelected ? '#ffffff' : 'var(--text-muted)', flexShrink: 0 }}>
                          {isVideo && (isProRes ? <Sparkles size={14} strokeWidth={2} /> : <Film size={14} strokeWidth={2} />)}
                          {isAudio && <Music size={14} strokeWidth={2} />}
                          {isImage && <ImageIcon size={14} strokeWidth={2} />}
                        </div>

                        <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
                          <div
                            style={{
                              fontSize: '11px',
                              fontWeight: 600,
                              color: isSelected ? '#ffffff' : 'var(--text-primary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              lineHeight: '1.3',
                            }}
                            title={qLabel}
                          >
                            {qLabel}
                          </div>
                          <div
                            style={{
                              fontSize: '9.5px',
                              color: isSelected ? 'var(--text-secondary)' : 'var(--text-muted)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              marginTop: '1px',
                            }}
                          >
                            <span style={{ fontWeight: 600 }}>{fmtUpper}</span>
                            {asset.resolution ? ` • ${asset.resolution}` : ''}
                            {fSize ? ` • ${formatBytes(fSize)}` : ''}
                          </div>
                        </div>

                        {isSelected && (
                          <CheckCircle
                            size={13}
                            strokeWidth={2}
                            color="#ffffff"
                            style={{ flexShrink: 0 }}
                          />
                        )}
                      </div>
                    );
                  })}

                  {/* Switch to Custom Card */}
                  <div
                    onClick={() => {
                      setQualityMode('custom');
                      if (!customQualityAssetId && mediaInfo.assets && mediaInfo.assets.length > 0) {
                        setCustomQualityAssetId(mediaInfo.assets[0].id);
                      }
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px dashed var(--border-strong)',
                      backgroundColor: 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.12s ease',
                      minHeight: '44px',
                      opacity: 0.85,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255, 255, 255, 0.4)';
                      (e.currentTarget as HTMLElement).style.opacity = '1';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)';
                      (e.currentTarget as HTMLElement).style.opacity = '0.85';
                    }}
                  >
                    <SlidersHorizontal size={13} strokeWidth={2} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                        + Custom Options...
                      </div>
                      <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
                        Configure Type, Quality & Codec
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: CUSTOM CONFIGURATION DROPDOWNS */}
            {qualityMode === 'custom' && (
              <div
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: 'var(--shadow-xs)',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                  {/* Dropdown 1: Media Type */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      1. Media Type
                    </label>
                    <select
                      className="input"
                      value={customMediaType}
                      onChange={(e) => handleCustomMediaTypeChange(e.target.value as 'video' | 'audio' | 'image')}
                      style={{
                        height: '32px',
                        fontSize: '11px',
                        fontWeight: 500,
                        backgroundColor: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-default)',
                        cursor: 'pointer',
                      }}
                    >
                      <option value="video">Video & Audio</option>
                      <option value="audio">Audio Only (Stem / Score)</option>
                      {imageAssets.length > 0 && <option value="image">Artwork / Thumbnail</option>}
                    </select>
                  </div>

                  {/* Dropdown 2: Stream Quality / Resolution */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      2. Stream Quality
                    </label>
                    <select
                      className="input"
                      value={customQualityAssetId}
                      onChange={(e) => setCustomQualityAssetId(e.target.value)}
                      style={{
                        height: '32px',
                        fontSize: '11px',
                        fontWeight: 500,
                        backgroundColor: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-default)',
                        cursor: 'pointer',
                      }}
                    >
                      {customMediaType === 'video' &&
                        (videoAssets.length > 0 ? (
                          videoAssets.map((asset) => {
                            const qLabel = asset.qualityLabel || (asset as any).quality_label || asset.id;
                            const res = asset.resolution ? ` (${asset.resolution})` : '';
                            const fSize = asset.filesizeApprox ? ` • ${formatBytes(asset.filesizeApprox)}` : '';
                            return (
                              <option key={asset.id} value={asset.id}>
                                {qLabel}{res}{fSize}
                              </option>
                            );
                          })
                        ) : (
                          <>
                            <option value="best_video">Best Quality Video</option>
                            <option value="1080p">1080p Full HD</option>
                            <option value="720p">720p HD</option>
                          </>
                        ))}

                      {customMediaType === 'audio' &&
                        (audioAssets.length > 0 ? (
                          audioAssets.map((asset) => {
                            const qLabel = asset.qualityLabel || (asset as any).quality_label || asset.id;
                            const fSize = asset.filesizeApprox ? ` • ${formatBytes(asset.filesizeApprox)}` : '';
                            return (
                              <option key={asset.id} value={asset.id}>
                                {qLabel}{fSize}
                              </option>
                            );
                          })
                        ) : (
                          <>
                            <option value="audio_wav">Broadcast WAV (48kHz Uncompressed)</option>
                            <option value="audio_mp3_320">MP3 (320kbps High Quality)</option>
                            <option value="audio_aac">AAC / M4A (320kbps Audio)</option>
                          </>
                        ))}

                      {customMediaType === 'image' &&
                        (imageAssets.length > 0 ? (
                          imageAssets.map((asset) => {
                            const qLabel = asset.qualityLabel || (asset as any).quality_label || asset.id;
                            const res = asset.resolution ? ` (${asset.resolution})` : '';
                            return (
                              <option key={asset.id} value={asset.id}>
                                {qLabel}{res}
                              </option>
                            );
                          })
                        ) : (
                          <option value="thumbnail_image">Full Resolution Cover Artwork</option>
                        ))}
                    </select>
                  </div>

                  {/* Dropdown 3: Target Output Codec / Format */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      3. Output Format / Codec
                    </label>
                    <select
                      className="input"
                      value={customFormat}
                      onChange={(e) => setCustomFormat(e.target.value)}
                      style={{
                        height: '32px',
                        fontSize: '11px',
                        fontWeight: 500,
                        backgroundColor: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-default)',
                        cursor: 'pointer',
                      }}
                    >
                      {customMediaType === 'video' && (
                        <>
                          <option value="mp4">MP4 (H.264 / AAC) — Universal NLE</option>
                          <option value="mov">MOV (Apple ProRes 422) — Post-Master</option>
                          <option value="webm">WebM (VP9 / Opus) — Original Stream</option>
                        </>
                      )}

                      {customMediaType === 'audio' && (
                        <>
                          <option value="wav">WAV (48kHz PCM) — Studio Standard</option>
                          <option value="mp3">MP3 (320kbps CBR) — High Quality</option>
                          <option value="m4a">M4A / AAC (320kbps) — Native Streaming</option>
                          <option value="flac">FLAC — Lossless Audio</option>
                        </>
                      )}

                      {customMediaType === 'image' && (
                        <>
                          <option value="jpg">JPG — Standard Photo</option>
                          <option value="png">PNG — Lossless RGB</option>
                          <option value="webp">WebP — Web Format</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>

                {/* Pipeline Summary & Preview Info */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '8px',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Active Pipeline:</span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {customMediaType === 'video' && customFormat === 'mov'
                        ? 'FFmpeg ProRes 422 Master Transcoder'
                        : customMediaType === 'audio' && customFormat === 'wav'
                        ? 'FFmpeg 48kHz PCM Audio Extractor'
                        : customMediaType === 'audio' && customFormat === 'mp3'
                        ? 'FFmpeg LAME 320kbps MP3 Encoder'
                        : 'Direct NLE-Optimized Stream Remux'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--success)', fontWeight: 600 }}>
                    <CheckCircle size={11} strokeWidth={2} />
                    <span>NLE Import Ready ({customFormat.toUpperCase()})</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-subtle)' }} />

          {/* Destination & Action */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                Bin:
              </span>
              <input
                type="text"
                className="input"
                value={targetBin}
                onChange={(e) => setTargetBin(e.target.value)}
                placeholder="Xdrop"
                style={{ height: '30px', fontSize: '11px', flex: '1 1 120px', minWidth: '100px' }}
              />

              {/* Auto-import Checkbox + Software Selection Dropdown */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  <input
                    type="checkbox"
                    checked={autoImport}
                    onChange={(e) => setAutoImport(e.target.checked)}
                    style={{ width: '13px', height: '13px', accentColor: '#ffffff', cursor: 'pointer' }}
                  />
                  <span style={{ color: 'var(--text-primary)' }}>Auto-import</span>
                </label>

                {autoImport && (
                  <select
                    className="input"
                    value={autoImportEditor}
                    onChange={(e) => {
                      setAutoImportEditor(e.target.value as 'resolve' | 'premiere' | 'aftereffects');
                      setUserSelectedEditor(true);
                    }}
                    style={{
                      height: '30px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      fontWeight: 500,
                      borderRadius: 'var(--radius-xs)',
                      border: '1px solid var(--border-default)',
                      backgroundColor: 'var(--bg-tertiary)',
                      color: 'var(--text-primary)',
                      boxShadow: 'none',
                      cursor: 'pointer',
                      width: 'auto',
                      minWidth: '130px',
                    }}
                    title="Select software to automatically import media into after download"
                  >
                    <option value="resolve">DaVinci Resolve</option>
                    <option value="premiere">Premiere Pro</option>
                    <option value="aftereffects">After Effects</option>
                  </select>
                )}
              </div>
            </div>

            {/* Action Buttons: Primary Download CTA Button */}
            <div style={{ display: 'flex', gap: '6px', width: '100%', alignItems: 'center' }}>
              <button
                type="button"
                className="btn btn-primary btn-lg"
                onClick={() => handleStartDownload()}
                disabled={isSubmitting || (qualityMode === 'presets' && !selectedAsset)}
                style={{ flex: 1, padding: '8px 14px', fontSize: '11.5px', fontWeight: 600 }}
              >
                {autoImport ? (
                  autoImportEditor === 'aftereffects' ? (
                    <Sparkles size={13} strokeWidth={2} />
                  ) : autoImportEditor === 'premiere' ? (
                    <Layers size={13} strokeWidth={2} />
                  ) : (
                    <Film size={13} strokeWidth={2} />
                  )
                ) : (
                  <Download size={13} strokeWidth={2} />
                )}
                <span>
                  {autoImport
                    ? `Auto-import ${qualityMode === 'custom' ? `Custom ${customFormat.toUpperCase()} ` : ''}to ${
                        autoImportEditor === 'resolve'
                          ? 'DaVinci Resolve'
                          : autoImportEditor === 'premiere'
                          ? 'Premiere Pro'
                          : 'After Effects'
                      }`
                    : `Download ${qualityMode === 'custom' ? `Custom ${customFormat.toUpperCase()}` : 'Asset Only'}`}
                </span>
                <ArrowRight size={12} strokeWidth={2} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
