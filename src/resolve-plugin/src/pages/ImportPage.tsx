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
  Check,
  AlertTriangle,
  Folder,
  Layers,
  ArrowRight,
  SlidersHorizontal,
  Download,
  Loader2,
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

  // Quick mode selection: 'video' | 'audio' | 'custom'
  const [smartMode, setSmartMode] = useState<'video' | 'audio' | 'custom'>('video');

  // Custom configuration dropdown states
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

  // Find the single best video asset (highest resolution / default)
  const bestVideoAsset = useMemo(() => {
    if (videoAssets.length === 0) return (mediaInfo?.assets || [])[0] || null;
    return videoAssets.find((a) => a.isDefault || (a as any).is_default) || videoAssets[0];
  }, [videoAssets, mediaInfo]);

  // Find the best audio asset
  const bestAudioAsset = useMemo(() => {
    if (audioAssets.length === 0) return null;
    return audioAssets.find((a) => a.isDefault || (a as any).is_default) || audioAssets[0];
  }, [audioAssets]);

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
      setSmartMode('video');
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

    if (smartMode === 'audio') {
      mediaType = 'audio';
      format = 'wav';
      qualityLabel = 'Studio Audio (WAV)';
      extractAudioOnly = true;
      transcodeAfmt = 'wav';
      assetId = bestAudioAsset ? bestAudioAsset.id : (selectedAssetId || 'audio_wav');
    } else if (smartMode === 'custom') {
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
      // Smart Video (Default / Best Quality)
      const asset = (mediaInfo.assets || []).find((a) => a.id === selectedAssetId) || bestVideoAsset;
      if (!asset) return;

      assetId = asset.id;
      format = asset.format || 'mp4';
      qualityLabel = asset.qualityLabel || (asset as any).quality_label || (asset.format || 'MP4').toUpperCase();
      mediaType = asset.mediaType || (asset as any).media_type || 'video';
      extractAudioOnly = false;
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

  const editorDisplayName = useMemo(() => {
    switch (autoImportEditor) {
      case 'premiere':
        return 'Premiere Pro';
      case 'resolve':
        return 'DaVinci Resolve';
      case 'aftereffects':
        return 'After Effects';
      case 'audition':
        return 'Audition';
      default:
        return 'Editor';
    }
  }, [autoImportEditor]);

  return (
    <div style={{ padding: '8px 10px', maxWidth: '640px', margin: '0 auto' }}>
      {/* 1. Search & Command Input */}
      <div
        className="panel"
        style={{
          marginBottom: '8px',
          padding: '8px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
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
                paddingLeft: '30px',
                paddingRight: urlInput ? (detectedPlatform ? '120px' : '54px') : '30px',
                height: '34px',
                fontSize: '11px',
                fontWeight: 450,
              }}
            />

            {/* Left Search Icon */}
            <div
              style={{
                position: 'absolute',
                left: '9px',
                top: '9px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-muted)',
              }}
            >
              <Search size={13} strokeWidth={2} />
            </div>

            {/* Right Action Cluster: Detected Platform Pill, Clear & Paste */}
            <div
              style={{
                position: 'absolute',
                right: '6px',
                top: '5px',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              {detectedPlatform && (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    lineHeight: '1.2',
                    userSelect: 'none',
                  }}
                >
                  {detectedPlatform.name}
                </span>
              )}

              {urlInput && (
                <button
                  type="button"
                  onClick={handleClearInput}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '3px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: 'var(--radius-xs)',
                  }}
                  title="Clear input"
                >
                  <X size={12} />
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
                  padding: '3px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 'var(--radius-xs)',
                }}
                title="Paste from clipboard"
              >
                <Clipboard size={12} />
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
              height: '34px',
              padding: '0 12px',
              fontSize: '11px',
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={12} className="spin" />
                <span>Fetching...</span>
              </>
            ) : (
              <>
                <Sparkles size={12} strokeWidth={2.2} />
                <span>Fetch</span>
              </>
            )}
          </button>
        </div>

        {/* Clean, quiet supported platforms note */}
        {!urlInput && (
          <div
            style={{
              fontSize: '9.5px',
              color: 'var(--text-muted)',
              paddingLeft: '2px',
              letterSpacing: '0.01em',
            }}
          >
            Supports YouTube, TikTok, Instagram, X, Vimeo, and direct media files.
          </div>
        )}

        {/* Error Notification */}
        {analysisError && (
          <div
            style={{
              padding: '6px 9px',
              backgroundColor: 'var(--danger-subtle)',
              border: '1px solid var(--danger-border)',
              borderRadius: 'var(--radius-xs)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '6px',
              fontSize: '10.5px',
              color: 'var(--danger)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <AlertTriangle size={12} strokeWidth={2} style={{ flexShrink: 0 }} />
              <span>{analysisError}</span>
            </div>
            <button
              onClick={() => setAnalysisError(null)}
              style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '1px' }}
            >
              <X size={11} />
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
            padding: '34px 16px',
            gap: '8px',
            backgroundColor: 'transparent',
            border: '1px dashed var(--border-default)',
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <Download size={15} strokeWidth={2} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Paste any media link above
            </h4>
            <p style={{ fontSize: '10px', color: 'var(--text-muted)', maxWidth: '300px', lineHeight: 1.4 }}>
              Xdrop inspects the highest quality video and audio streams, transcode-free, straight into your editor bin.
            </p>
          </div>
        </div>
      )}

      {/* 3. Inspected Media Showcase (Progressive Disclosure & 1-Click Import) */}
      {mediaInfo && (
        <div
          className="panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            padding: '10px 12px',
          }}
        >
          {/* Media Header (Thumbnail + Title + Metadata) */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {thumbSrc && !thumbError ? (
              <div
                style={{
                  position: 'relative',
                  width: '96px',
                  height: '54px',
                  borderRadius: 'var(--radius-xs)',
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
                      bottom: '2px',
                      right: '2px',
                      backgroundColor: 'rgba(0,0,0,0.85)',
                      color: '#ffffff',
                      fontSize: '8px',
                      fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
                      padding: '1px 3px',
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
                  width: '96px',
                  height: '54px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                  flexShrink: 0,
                }}
              >
                <Film size={18} strokeWidth={2} />
              </div>
            )}

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '2px' }}>
                <span className="badge badge-neutral" style={{ fontSize: '8.5px', padding: '1px 4px' }}>
                  {mediaInfo.platformName || mediaInfo.platform || 'Media'}
                </span>
                {mediaInfo.author && (
                  <span
                    style={{
                      fontSize: '9.5px',
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
                  fontSize: '11.5px',
                  fontWeight: 600,
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

          {/* Mode Switcher: 3 Clean Chips (Video, Audio, Custom) */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-default)',
              padding: '2px',
              gap: '2px',
            }}
          >
            <button
              type="button"
              onClick={() => {
                setSmartMode('video');
                if (bestVideoAsset) setSelectedAssetId(bestVideoAsset.id);
              }}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                padding: '4px 8px',
                fontSize: '10.5px',
                fontWeight: smartMode === 'video' ? 600 : 500,
                borderRadius: 'var(--radius-xs)',
                border: smartMode === 'video' ? '1px solid var(--border-strong)' : '1px solid transparent',
                backgroundColor: smartMode === 'video' ? 'var(--bg-elevated)' : 'transparent',
                color: smartMode === 'video' ? '#ffffff' : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              <Film size={11} strokeWidth={smartMode === 'video' ? 2.2 : 1.8} />
              <span>Best Video</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setSmartMode('audio');
                if (bestAudioAsset) setSelectedAssetId(bestAudioAsset.id);
              }}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                padding: '4px 8px',
                fontSize: '10.5px',
                fontWeight: smartMode === 'audio' ? 600 : 500,
                borderRadius: 'var(--radius-xs)',
                border: smartMode === 'audio' ? '1px solid var(--border-strong)' : '1px solid transparent',
                backgroundColor: smartMode === 'audio' ? 'var(--bg-elevated)' : 'transparent',
                color: smartMode === 'audio' ? '#ffffff' : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              <Music size={11} strokeWidth={smartMode === 'audio' ? 2.2 : 1.8} />
              <span>Audio Only</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setSmartMode('custom');
                const targetAsset = (mediaInfo.assets || []).find((a) => a.id === selectedAssetId) || mediaInfo.assets?.[0];
                if (targetAsset) {
                  const mType = ((targetAsset.mediaType || (targetAsset as any).media_type || 'video') as 'video' | 'audio' | 'image');
                  setCustomMediaType(mType);
                  setCustomQualityAssetId(targetAsset.id);
                  setCustomFormat(targetAsset.format || (mType === 'audio' ? 'wav' : 'mp4'));
                }
              }}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '5px',
                padding: '4px 8px',
                fontSize: '10.5px',
                fontWeight: smartMode === 'custom' ? 600 : 500,
                borderRadius: 'var(--radius-xs)',
                border: smartMode === 'custom' ? '1px solid var(--border-strong)' : '1px solid transparent',
                backgroundColor: smartMode === 'custom' ? 'var(--bg-elevated)' : 'transparent',
                color: smartMode === 'custom' ? '#ffffff' : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }}
            >
              <SlidersHorizontal size={11} strokeWidth={smartMode === 'custom' ? 2.2 : 1.8} />
              <span>Custom...</span>
            </button>
          </div>

          {/* Mode Details / Selection Card */}
          {smartMode === 'video' && (
            <div
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-xs)',
                padding: '7px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#ffffff' }}>
                  {bestVideoAsset?.qualityLabel || (bestVideoAsset as any)?.quality_label || 'High Definition Video'}
                </span>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {(bestVideoAsset?.format || 'mp4').toUpperCase()}
                  {bestVideoAsset?.resolution ? ` • ${bestVideoAsset.resolution}` : ''}
                  {bestVideoAsset?.filesizeApprox ? ` • ~${formatBytes(bestVideoAsset.filesizeApprox)}` : ''}
                </span>
              </div>

              {/* Quick resolution switcher pills if multiple video formats exist */}
              {videoAssets.length > 1 && (
                <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  {videoAssets.slice(0, 4).map((vAsset) => {
                    const isSel = selectedAssetId === vAsset.id;
                    const resShort = vAsset.resolution ? vAsset.resolution.split('x')[1] ? `${vAsset.resolution.split('x')[1]}p` : vAsset.resolution : (vAsset.qualityLabel || 'HD');
                    return (
                      <button
                        key={vAsset.id}
                        type="button"
                        onClick={() => setSelectedAssetId(vAsset.id)}
                        style={{
                          fontSize: '8.5px',
                          fontWeight: isSel ? 600 : 450,
                          padding: '2px 5px',
                          borderRadius: 'var(--radius-xs)',
                          border: isSel ? '1px solid #ffffff' : '1px solid var(--border-subtle)',
                          backgroundColor: isSel ? 'var(--bg-elevated)' : 'transparent',
                          color: isSel ? '#ffffff' : 'var(--text-muted)',
                          cursor: 'pointer',
                        }}
                      >
                        {resShort}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {smartMode === 'audio' && (
            <div
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-xs)',
                padding: '7px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#ffffff' }}>
                  Studio Master Audio (WAV)
                </span>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  48kHz 24-bit PCM Uncompressed • Lossless
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--success)', fontSize: '9px', fontWeight: 600 }}>
                <Check size={11} strokeWidth={2.5} />
                <span>Ready</span>
              </div>
            </div>
          )}

          {smartMode === 'custom' && (
            <div
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-xs)',
                padding: '8px 10px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: '6px',
              }}
            >
              {/* Dropdown 1: Media Type */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <label style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Type
                </label>
                <select
                  className="input"
                  value={customMediaType}
                  onChange={(e) => handleCustomMediaTypeChange(e.target.value as 'video' | 'audio' | 'image')}
                  style={{ height: '28px', fontSize: '10.5px', backgroundColor: 'var(--bg-secondary)' }}
                >
                  <option value="video">Video & Audio</option>
                  <option value="audio">Audio Only</option>
                  {imageAssets.length > 0 && <option value="image">Artwork / Cover</option>}
                </select>
              </div>

              {/* Dropdown 2: Stream Quality / Resolution */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <label style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Stream Quality
                </label>
                <select
                  className="input"
                  value={customQualityAssetId}
                  onChange={(e) => setCustomQualityAssetId(e.target.value)}
                  style={{ height: '28px', fontSize: '10.5px', backgroundColor: 'var(--bg-secondary)' }}
                >
                  {customMediaType === 'video' &&
                    (videoAssets.length > 0 ? (
                      videoAssets.map((asset) => {
                        const qLabel = asset.qualityLabel || (asset as any).quality_label || asset.id;
                        const res = asset.resolution ? ` (${asset.resolution})` : '';
                        return (
                          <option key={asset.id} value={asset.id}>
                            {qLabel}{res}
                          </option>
                        );
                      })
                    ) : (
                      <>
                        <option value="best_video">Best Quality Available</option>
                        <option value="video_2160p">4K Ultra HD (2160p)</option>
                        <option value="video_1080p">1080p Full HD</option>
                      </>
                    ))}

                  {customMediaType === 'audio' &&
                    (audioAssets.length > 0 ? (
                      audioAssets.map((asset) => {
                        const qLabel = asset.qualityLabel || (asset as any).quality_label || asset.id;
                        return (
                          <option key={asset.id} value={asset.id}>
                            {qLabel}
                          </option>
                        );
                      })
                    ) : (
                      <>
                        <option value="audio_wav">WAV (48kHz Uncompressed)</option>
                        <option value="audio_mp3_320">MP3 (320kbps)</option>
                      </>
                    ))}

                  {customMediaType === 'image' && (
                    <option value="thumbnail_image">Full Resolution Cover</option>
                  )}
                </select>
              </div>

              {/* Dropdown 3: Target Codec / Container */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <label style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Format
                </label>
                <select
                  className="input"
                  value={customFormat}
                  onChange={(e) => setCustomFormat(e.target.value)}
                  style={{ height: '28px', fontSize: '10.5px', backgroundColor: 'var(--bg-secondary)' }}
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
                    </>
                  )}
                </select>
              </div>
            </div>
          )}

          {/* Destination Strip & Action CTA */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '2px' }}>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: 1, minWidth: 0 }}>
                <Folder size={12} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                <input
                  type="text"
                  className="input"
                  value={targetBin}
                  onChange={(e) => setTargetBin(e.target.value)}
                  placeholder="000_Xdrop Assets"
                  style={{ height: '28px', fontSize: '10.5px' }}
                  title="Target project bin name"
                />
              </div>

              {/* Auto-import Checkbox + Software Dropdown */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  <input
                    type="checkbox"
                    checked={autoImport}
                    onChange={(e) => setAutoImport(e.target.checked)}
                    style={{ width: '12px', height: '12px', accentColor: '#ffffff', cursor: 'pointer' }}
                  />
                  <span style={{ color: 'var(--text-secondary)' }}>Auto-import</span>
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
                      height: '28px',
                      padding: '1px 6px',
                      fontSize: '10.5px',
                      backgroundColor: 'var(--bg-tertiary)',
                      width: 'auto',
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
              className="btn btn-primary"
              onClick={() => handleStartDownload()}
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '6px 12px',
                fontSize: '11.5px',
                fontWeight: 600,
                height: '34px',
                gap: '6px',
              }}
            >
              {autoImport ? (
                autoImportEditor === 'aftereffects' ? (
                  <Sparkles size={12} strokeWidth={2.2} />
                ) : autoImportEditor === 'premiere' ? (
                  <Layers size={12} strokeWidth={2.2} />
                ) : (
                  <Film size={12} strokeWidth={2.2} />
                )
              ) : (
                <Download size={12} strokeWidth={2.2} />
              )}
              <span>
                {autoImport ? `Import to ${editorDisplayName}` : 'Download Media'}
              </span>
              <ArrowRight size={12} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
