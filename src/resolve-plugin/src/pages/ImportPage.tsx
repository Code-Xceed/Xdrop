import React, { useState, useEffect, useMemo } from 'react';
import { MediaInfo } from '@xdrop/shared-types';
import { formatBytes, formatDuration, extractUrlsFromText } from '@xdrop/utilities';
import { useEditorContext } from '../context/EditorContext';
import { analyzeUrl, createDownload } from '../services/api';
import {
  Search,
  Clipboard,
  X,
  Sparkles,
  Film,
  Music,
  ImageIcon,
  CheckCircle2,
  AlertTriangle,
  Folder,
  Layers,
  ArrowRight,
  SlidersHorizontal,
  Zap,
  Radio,
  Download,
} from 'lucide-react';

interface ImportPageProps {
  onJobStarted: () => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export interface PlatformDef {
  id: string;
  name: string;
  regex: RegExp;
  placeholder: string;
}

export const SUPPORTED_PLATFORMS: PlatformDef[] = [
  {
    id: 'youtube',
    name: 'YouTube',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.|music\.)?youtube\.com\/(?:watch\?|shorts\/|embed\/|live\/|v\/|clip\/)|youtu\.be\/)/i,
    placeholder: 'https://youtube.com/watch?v=...',
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    regex: /(?:https?:\/\/)?(?:(?:www\.|vm\.|vt\.|m\.)?tiktok\.com\/)/i,
    placeholder: 'https://tiktok.com/@creator/video/...',
  },
  {
    id: 'instagram',
    name: 'Instagram',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.)?instagram\.com|instagr\.am)\/(?:reel|reels|p|tv|stories|share)\//i,
    placeholder: 'https://instagram.com/reel/...',
  },
  {
    id: 'x',
    name: 'X (Twitter)',
    regex: /(?:https?:\/\/)?(?:(?:www\.|mobile\.)?(?:twitter\.com|x\.com)\/(?:[^/]+\/status\/\d+|i\/status\/\d+)|t\.co\/[a-zA-Z0-9]+)/i,
    placeholder: 'https://x.com/user/status/...',
  },
  {
    id: 'vimeo',
    name: 'Vimeo',
    regex: /(?:https?:\/\/)?(?:(?:www\.|player\.)?vimeo\.com\/(?:channels\/[^/]+\/|groups\/[^/]+\/videos\/|showcase\/[^/]+\/video\/|manage\/videos\/|video\/)?\d+)/i,
    placeholder: 'https://vimeo.com/...',
  },
  {
    id: 'reddit',
    name: 'Reddit',
    regex: /(?:https?:\/\/)?(?:(?:www\.|old\.|new\.|m\.)?reddit\.com\/(?:r\/[^/]+\/(?:comments|s)\/|clip\/)|v\.redd\.it\/[a-zA-Z0-9]+|redd\.it\/[a-zA-Z0-9]+)/i,
    placeholder: 'https://reddit.com/r/videos/...',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    regex: /(?:https?:\/\/)?(?:(?:www\.|m\.|fb\.)?facebook\.com\/(?:watch\/?\?|reel\/|reels\/|share\/[rv]\/|[^/]+\/videos\/)|fb\.watch\/[a-zA-Z0-9_\-]+)/i,
    placeholder: 'https://fb.watch/...',
  },
  {
    id: 'direct',
    name: 'Direct Media',
    regex: /\.(mp4|mov|webm|m4v|mkv|avi|flv|mp3|wav|m4a|aac|flac|ogg|aiff|jpg|jpeg|png|webp)(\?.*)?$/i,
    placeholder: 'https://.../video.mp4',
  },
];

export function detectPlatformFromUrl(inputUrl: string): PlatformDef | null {
  const trimmed = inputUrl.trim();
  if (!trimmed) return null;

  for (const plat of SUPPORTED_PLATFORMS) {
    if (plat.regex.test(trimmed)) {
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
  const [targetBin, setTargetBin] = useState('000_Xdrop Assets');
  const [autoImport, setAutoImport] = useState(true);
  const [autoImportEditor, setAutoImportEditor] = useState<'resolve' | 'premiere' | 'aftereffects' | 'audition'>(() => {
    if (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'audition' || activeEditor === 'resolve') {
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

  useEffect(() => {
    if (!userSelectedEditor && (activeEditor === 'premiere' || activeEditor === 'aftereffects' || activeEditor === 'resolve' || activeEditor === 'audition')) {
      setAutoImportEditor(activeEditor);
    }
  }, [activeEditor, userSelectedEditor]);

  // Thumbnail state
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
      setThumbSrc(proxyUrl);
    } else {
      setThumbError(true);
    }
  };

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

  const handleAnalyze = async () => {
    const urls = extractUrlsFromText(urlInput);
    if (urls.length === 0) {
      setAnalysisError('Please enter a valid video or media link.');
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
      setAnalysisError(err.message || 'Could not fetch media from this link.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !urlInput.includes('\n'))) {
      e.preventDefault();
      if (mediaInfo) {
        handleStartDownload();
      } else {
        handleAnalyze();
      }
    }
  };

  const handleStartDownload = async (overrideEditor?: 'resolve' | 'premiere' | 'aftereffects' | 'audition') => {
    if (!mediaInfo) return;
    const editorToUse = overrideEditor || (autoImport ? autoImportEditor : 'none');

    let assetId = selectedAssetId;
    let format = 'mp4';
    let qualityLabel = 'Best Quality';
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
        qualityLabel = `Audio (${customFormat.toUpperCase()})`;
        transcodeAfmt = customFormat;
      } else {
        assetId = 'thumbnail_image';
        qualityLabel = 'Artwork';
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
        target_audition_bin: targetBin,
        auto_import_to_audition: autoImport && editorToUse === 'audition',
        transcode_video_format: transcodeVfmt,
        transcode_audio_format: transcodeAfmt,
        extract_audio_only: extractAudioOnly,
      });

      showToast(`Added to queue: ${mediaInfo.title}`, 'success');
      onJobStarted();
    } catch (err: any) {
      showToast(err.message || 'Failed to queue download.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedAsset = mediaInfo?.assets?.find((a) => a.id === selectedAssetId);

  return (
    <div style={{ padding: '8px 10px', maxWidth: '780px', margin: '0 auto' }}>
      {/* 1. Main Search & Command Bar */}
      <div
        className="panel"
        style={{
          marginBottom: '10px',
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              className="input"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste media link from YouTube, TikTok, Instagram, X..."
              style={{
                paddingLeft: '32px',
                paddingRight: urlInput ? '56px' : '32px',
                height: '36px',
                fontSize: '11.5px',
                fontWeight: 450,
              }}
            />

            {/* Left Dynamic Icon */}
            <div
              style={{
                position: 'absolute',
                left: '10px',
                top: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: detectedPlatform ? '#ffffff' : 'var(--text-muted)',
                transition: 'color 120ms ease',
              }}
            >
              {detectedPlatform ? (
                <Radio size={14} strokeWidth={2.2} />
              ) : (
                <Search size={14} strokeWidth={2} />
              )}
            </div>

            {/* Right Icons: Clear & Paste */}
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

          {/* Fetch Button */}
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
                <span className="spin">
                  <Sparkles size={13} />
                </span>
                <span>Inspecting...</span>
              </>
            ) : (
              <>
                <Sparkles size={13} strokeWidth={2.2} />
                <span>Fetch</span>
              </>
            )}
          </button>
        </div>

        {/* Minimal Platform Strip */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            overflowX: 'auto',
            scrollbarWidth: 'none',
          }}
        >
          {SUPPORTED_PLATFORMS.map((plat) => {
            const isMatched = detectedPlatform?.id === plat.id;
            return (
              <span
                key={plat.id}
                style={{
                  fontSize: '9.5px',
                  fontWeight: isMatched ? 600 : 450,
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                  border: isMatched ? '1px solid rgba(255, 255, 255, 0.3)' : '1px solid var(--border-subtle)',
                  backgroundColor: isMatched ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                  color: isMatched ? '#ffffff' : 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  lineHeight: '1.3',
                  flexShrink: 0,
                  transition: 'all 120ms ease',
                }}
              >
                {plat.name}
              </span>
            );
          })}
        </div>

        {/* Error Notification */}
        {analysisError && (
          <div
            style={{
              padding: '8px 10px',
              backgroundColor: 'var(--danger-subtle)',
              border: '1px solid var(--danger-border)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              fontSize: '11px',
              color: 'var(--danger)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertTriangle size={13} strokeWidth={2} style={{ flexShrink: 0 }} />
              <span>{analysisError}</span>
            </div>
            <button
              onClick={() => setAnalysisError(null)}
              style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '2px' }}
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* 2. Empty State (When no media is loaded) */}
      {!mediaInfo && !isAnalyzing && (
        <div
          className="panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '40px 20px',
            gap: '10px',
            backgroundColor: 'transparent',
            border: '1px dashed var(--border-default)',
          }}
        >
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-strong)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
            }}
          >
            <Download size={18} strokeWidth={2} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <h4 style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Paste any media link above
            </h4>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', maxWidth: '340px', lineHeight: 1.4 }}>
              YouTube, TikTok, Instagram, X, and Vimeo files are fetched in the highest available resolution and placed directly into your editor bin.
            </p>
          </div>
        </div>
      )}

      {/* 3. Inspected Media Showcase */}
      {mediaInfo && (
        <div
          className="panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            padding: '12px',
          }}
        >
          {/* Media Header */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
            {thumbSrc && !thumbError ? (
              <div
                style={{
                  position: 'relative',
                  width: '120px',
                  height: '68px',
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
                      backgroundColor: 'rgba(0,0,0,0.85)',
                      color: '#ffffff',
                      fontSize: '8.5px',
                      fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
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
                  width: '120px',
                  height: '68px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                }}
              >
                <Film size={20} strokeWidth={2} />
              </div>
            )}

            <div style={{ flex: 1, minWidth: '180px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                <span className="badge badge-neutral">
                  {mediaInfo.platformName || mediaInfo.platform || 'Media'}
                </span>
                {mediaInfo.author && (
                  <span
                    style={{
                      fontSize: '10.5px',
                      color: 'var(--text-muted)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {mediaInfo.author}
                  </span>
                )}
              </div>

              <h3
                style={{
                  fontSize: '12.5px',
                  fontWeight: 600,
                  lineHeight: 1.35,
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

          {/* Quality Mode Switcher */}
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '8px',
              }}
            >
              {/* Segmented Control */}
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: '6px',
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
                    gap: '4px',
                    padding: '3px 8px',
                    fontSize: '10.5px',
                    fontWeight: qualityMode === 'presets' ? 600 : 500,
                    borderRadius: '4px',
                    border: qualityMode === 'presets' ? '1px solid var(--border-strong)' : '1px solid transparent',
                    backgroundColor: qualityMode === 'presets' ? 'var(--bg-elevated)' : 'transparent',
                    color: qualityMode === 'presets' ? '#ffffff' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 120ms ease',
                    boxShadow: qualityMode === 'presets' ? '0 1px 2px rgba(0,0,0,0.4)' : 'none',
                  }}
                >
                  <Zap size={11} strokeWidth={2.2} />
                  <span>Presets</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setQualityMode('custom');
                    const targetAsset = (mediaInfo.assets || []).find((a) => a.id === selectedAssetId) || mediaInfo.assets?.[0];
                    if (targetAsset) {
                      const mType = ((targetAsset.mediaType || (targetAsset as any).media_type || 'video') as 'video' | 'audio' | 'image');
                      setCustomMediaType(mType);
                      setCustomQualityAssetId(targetAsset.id);
                      setCustomFormat(targetAsset.format || (mType === 'audio' ? 'wav' : 'mp4'));
                    }
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 8px',
                    fontSize: '10.5px',
                    fontWeight: qualityMode === 'custom' ? 600 : 500,
                    borderRadius: '4px',
                    border: qualityMode === 'custom' ? '1px solid var(--border-strong)' : '1px solid transparent',
                    backgroundColor: qualityMode === 'custom' ? 'var(--bg-elevated)' : 'transparent',
                    color: qualityMode === 'custom' ? '#ffffff' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 120ms ease',
                    boxShadow: qualityMode === 'custom' ? '0 1px 2px rgba(0,0,0,0.4)' : 'none',
                  }}
                >
                  <SlidersHorizontal size={11} strokeWidth={2.2} />
                  <span>Custom Settings</span>
                </button>
              </div>

              {/* Category Filters (when in presets mode) */}
              {qualityMode === 'presets' && (
                <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
                  {[
                    { id: 'all', label: 'All' },
                    { id: 'video', label: 'Video' },
                    { id: 'audio', label: 'Audio' },
                  ].map((cat) => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setPresetCategory(cat.id as any)}
                      style={{
                        padding: '2px 6px',
                        fontSize: '9.5px',
                        fontWeight: presetCategory === cat.id ? 600 : 500,
                        borderRadius: 'var(--radius-xs)',
                        border: 'none',
                        backgroundColor: presetCategory === cat.id ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                        color: presetCategory === cat.id ? '#ffffff' : 'var(--text-muted)',
                        cursor: 'pointer',
                        transition: 'all 120ms ease',
                      }}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* TAB 1: PRESETS MODE */}
            {qualityMode === 'presets' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '6px' }}>
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
                        padding: '7px 9px',
                        borderRadius: 'var(--radius-sm)',
                        border: isSelected
                          ? '1px solid #ffffff'
                          : '1px solid var(--border-default)',
                        backgroundColor: isSelected
                          ? 'var(--bg-elevated)'
                          : 'var(--bg-tertiary)',
                        boxShadow: isSelected ? '0 1px 4px rgba(0, 0, 0, 0.5)' : 'none',
                        cursor: 'pointer',
                        transition: 'all 100ms ease',
                        minHeight: '40px',
                      }}
                    >
                      <div style={{ color: isSelected ? '#ffffff' : 'var(--text-muted)', flexShrink: 0 }}>
                        {isVideo && (isProRes ? <Sparkles size={13} strokeWidth={2.2} /> : <Film size={13} strokeWidth={2} />)}
                        {isAudio && <Music size={13} strokeWidth={2} />}
                        {isImage && <ImageIcon size={13} strokeWidth={2} />}
                      </div>

                      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
                        <div
                          style={{
                            fontSize: '10.5px',
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
                            fontSize: '9px',
                            color: isSelected ? 'var(--text-secondary)' : 'var(--text-muted)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            fontFamily: 'var(--font-mono)',
                            marginTop: '1px',
                          }}
                        >
                          <span>{fmtUpper}</span>
                          {asset.resolution ? ` • ${asset.resolution}` : ''}
                          {fSize ? ` • ${formatBytes(fSize)}` : ''}
                        </div>
                      </div>

                      {isSelected && (
                        <CheckCircle2
                          size={13}
                          strokeWidth={2.5}
                          color="#ffffff"
                          style={{ flexShrink: 0 }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* TAB 2: CUSTOM CONFIGURATION */}
            {qualityMode === 'custom' && (
              <div
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                  {/* Dropdown 1: Media Type */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <label style={{ fontSize: '9.5px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      Media Type
                    </label>
                    <select
                      className="input"
                      value={customMediaType}
                      onChange={(e) => handleCustomMediaTypeChange(e.target.value as 'video' | 'audio' | 'image')}
                      style={{
                        height: '30px',
                        fontSize: '11px',
                        backgroundColor: 'var(--bg-secondary)',
                      }}
                    >
                      <option value="video">Video & Audio</option>
                      <option value="audio">Audio Only</option>
                      {imageAssets.length > 0 && <option value="image">Artwork / Cover</option>}
                    </select>
                  </div>

                  {/* Dropdown 2: Stream Quality / Resolution */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <label style={{ fontSize: '9.5px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      Stream Quality
                    </label>
                    <select
                      className="input"
                      value={customQualityAssetId}
                      onChange={(e) => setCustomQualityAssetId(e.target.value)}
                      style={{
                        height: '30px',
                        fontSize: '11px',
                        backgroundColor: 'var(--bg-secondary)',
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
                            <option value="best_video">Best Quality Available</option>
                            <option value="video_2160p">4K Ultra HD (2160p)</option>
                            <option value="video_1440p">2K Quad HD (1440p)</option>
                            <option value="video_1080p">1080p Full HD</option>
                            <option value="video_720p">720p HD</option>
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
                            <option value="audio_wav">WAV (48kHz Uncompressed)</option>
                            <option value="audio_mp3_320">MP3 (320kbps)</option>
                            <option value="audio_aac">AAC / M4A (320kbps)</option>
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
                          <option value="thumbnail_image">Full Resolution Cover</option>
                        ))}
                    </select>
                  </div>

                  {/* Dropdown 3: Target Output Codec / Format */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <label style={{ fontSize: '9.5px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      Output Format
                    </label>
                    <select
                      className="input"
                      value={customFormat}
                      onChange={(e) => setCustomFormat(e.target.value)}
                      style={{
                        height: '30px',
                        fontSize: '11px',
                        backgroundColor: 'var(--bg-secondary)',
                      }}
                    >
                      {customMediaType === 'video' && (
                        <>
                          <option value="mp4">MP4 (H.264 / AAC)</option>
                          <option value="mov">MOV (Apple ProRes 422)</option>
                          <option value="webm">WebM (VP9 / Opus)</option>
                        </>
                      )}

                      {customMediaType === 'audio' && (
                        <>
                          <option value="wav">WAV (48kHz PCM)</option>
                          <option value="mp3">MP3 (320kbps)</option>
                          <option value="m4a">M4A (320kbps)</option>
                          <option value="flac">FLAC (Lossless)</option>
                        </>
                      )}

                      {customMediaType === 'image' && (
                        <>
                          <option value="jpg">JPG</option>
                          <option value="png">PNG (Lossless)</option>
                          <option value="webp">WebP</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-subtle)' }} />

          {/* Destination Strip & Action CTA */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flex: '1 1 140px', minWidth: '120px' }}>
                <Folder size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                <input
                  type="text"
                  className="input"
                  value={targetBin}
                  onChange={(e) => setTargetBin(e.target.value)}
                  placeholder="000_Xdrop Assets"
                  style={{ height: '30px', fontSize: '11px' }}
                  title="Target project bin name"
                />
              </div>

              {/* Auto-import Checkbox + Software Dropdown */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap' }}>
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
                      setAutoImportEditor(e.target.value as 'resolve' | 'premiere' | 'aftereffects' | 'audition');
                      setUserSelectedEditor(true);
                    }}
                    style={{
                      height: '30px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      backgroundColor: 'var(--bg-tertiary)',
                      width: 'auto',
                      minWidth: '125px',
                    }}
                  >
                    <option value="resolve">DaVinci Resolve</option>
                    <option value="premiere">Premiere Pro</option>
                    <option value="aftereffects">After Effects</option>
                    <option value="audition">Audition</option>
                  </select>
                )}
              </div>
            </div>

            {/* Primary Action Button */}
            <button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={() => handleStartDownload()}
              disabled={isSubmitting || (qualityMode === 'presets' && !selectedAsset)}
              style={{
                width: '100%',
                padding: '8px 14px',
                fontSize: '12px',
                fontWeight: 600,
                height: '38px',
              }}
            >
              {autoImport ? (
                autoImportEditor === 'aftereffects' ? (
                  <Sparkles size={13} strokeWidth={2.2} />
                ) : autoImportEditor === 'premiere' ? (
                  <Layers size={13} strokeWidth={2.2} />
                ) : (
                  <Film size={13} strokeWidth={2.2} />
                )
              ) : (
                <Download size={13} strokeWidth={2.2} />
              )}
              <span>
                {autoImport
                  ? `Import to ${
                      autoImportEditor === 'resolve'
                        ? 'DaVinci Resolve'
                        : autoImportEditor === 'premiere'
                        ? 'Premiere Pro'
                        : autoImportEditor === 'aftereffects'
                        ? 'After Effects'
                        : 'Audition'
                    }`
                  : 'Download Media'}
              </span>
              <ArrowRight size={13} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
