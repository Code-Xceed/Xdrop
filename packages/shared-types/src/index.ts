/**
 * Xdrop Shared Domain Types
 * Single source of truth across frontend, backend contracts, and DaVinci Resolve bridge.
 */

export type PlatformId =
  | 'youtube'
  | 'instagram'
  | 'x'
  | 'reddit'
  | 'tiktok'
  | 'facebook'
  | 'pinterest'
  | 'vimeo'
  | 'direct'
  | 'generic';

export type MediaType = 'video' | 'audio' | 'image';

export type DownloadStatus =
  | 'queued'
  | 'downloading'
  | 'processing'
  | 'importing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface MediaAsset {
  id: string;
  mediaType: MediaType;
  format: string; // e.g. 'mp4', 'mov', 'wav', 'mp3', 'png'
  qualityLabel: string; // e.g. '1080p', '4K', '320kbps', 'Best'
  resolution?: string; // e.g. '1920x1080'
  fps?: number;
  vcodec?: string;
  acodec?: string;
  filesizeApprox?: number; // bytes
  url?: string;
  isDefault?: boolean;
}

export interface MediaInfo {
  url: string;
  platform: PlatformId;
  platformName: string;
  title: string;
  author?: string;
  authorUrl?: string;
  sourceId: string;
  duration?: number; // seconds
  thumbnailUrl?: string;
  description?: string;
  assets: MediaAsset[];
}

export interface DownloadOptions {
  assetId?: string;
  mediaType?: MediaType;
  format?: string;
  qualityLabel?: string;
  customFilename?: string;
  autoImportToResolve?: boolean;
  targetMediaPoolBin?: string;
  targetEditor?: SupportedEditor | 'auto';
  autoImportToPremiere?: boolean;
  targetPremiereBin?: string;
  autoImportToAfterEffects?: boolean;
  targetAfterEffectsBin?: string;
  transcodeVideoFormat?: string;
  transcodeAudioFormat?: string;
  extractAudioOnly?: boolean;
  generateProxy?: boolean;
}

export interface DownloadJob {
  id: string;
  sourceUrl: string;
  platform: PlatformId | string;
  title: string;
  author?: string;
  mediaType: MediaType;
  format: string;
  qualityLabel: string;
  status: DownloadStatus;
  progress: number; // 0 - 100
  speed?: string; // e.g. '14.2 MB/s'
  eta?: string; // e.g. '00:23'
  downloadedBytes: number;
  totalBytes?: number;
  outputFilePath?: string;
  thumbnailPath?: string;
  errorMessage?: string;
  resolveImported: boolean;
  resolveClipName?: string;
  premiereImported?: boolean;
  premiereBin?: string;
  aftereffectsImported?: boolean;
  aftereffectsBin?: string;
  targetEditor?: SupportedEditor;
  autoImport?: boolean;
  importedEditor?: SupportedEditor;
  importedClipName?: string;
  createdAt: string;
  completedAt?: string;
}

export type SupportedEditor = 'resolve' | 'premiere' | 'aftereffects' | 'none';

export interface ResolveStatus {
  isAvailable: boolean;
  version?: string;
  productName?: string;
  currentProject?: string;
  currentTimeline?: string;
  mediaPoolFolder?: string;
  error?: string;
  lastChecked: string;
}

export interface PremiereStatus {
  isAvailable: boolean;
  productName?: string;
  currentProject?: string;
  activeSequence?: string;
  projectPath?: string;
  error?: string;
  lastChecked: string;
}

export interface AfterEffectsStatus {
  isAvailable: boolean;
  productName?: string;
  currentProject?: string;
  activeSequence?: string; // Composition name
  projectPath?: string;
  error?: string;
  lastChecked: string;
}

export interface EditorsStatus {
  activeEditor: SupportedEditor;
  detectedHost?: SupportedEditor;
  resolve: ResolveStatus;
  premiere: PremiereStatus;
  aftereffects: AfterEffectsStatus;
}

export interface ResolveImportResult {
  success: boolean;
  clipName?: string;
  targetBin?: string;
  error?: string;
}

export interface PremiereImportResult {
  success: boolean;
  clipName?: string;
  targetBin?: string;
  error?: string;
}

export interface AfterEffectsImportResult {
  success: boolean;
  clipName?: string;
  targetBin?: string;
  error?: string;
}

export interface AppSettings {
  downloadDir: string;
  namingPattern: string; // e.g. "{project}/{platform}/{mediaType}/{title}_{quality}"
  concurrentDownloads: number;
  defaultEditor: SupportedEditor | 'auto';
  autoImportToResolve: boolean;
  targetMediaPoolBin: string;
  autoImportToPremiere: boolean;
  targetPremiereBin: string;
  autoImportToAfterEffects: boolean;
  targetAfterEffectsBin: string;
  overwriteExisting: boolean;
  ffmpegPath: string;
  preferredVideoFormat: 'mp4' | 'mov' | 'original';
  preferredAudioFormat: 'wav' | 'mp3' | 'aac' | 'original';
  generateProxy: boolean;
  proxyResolution: string;
  connectionTimeout: number; // seconds
  retryCount: number;
  localOnly: boolean;
  telemetryEnabled: boolean;
}

export interface LibraryItem {
  id: string;
  downloadJobId?: string;
  sourceUrl: string;
  platform: string;
  title: string;
  author?: string;
  mediaType: MediaType;
  format: string;
  resolution?: string;
  duration?: number;
  fileSizeBytes: number;
  filePath: string;
  thumbnailPath?: string;
  resolveImported: boolean;
  premiereImported?: boolean;
  aftereffectsImported?: boolean;
  createdAt: string;
}

export interface LibraryFilter {
  search?: string;
  platform?: string;
  mediaType?: MediaType;
  startDate?: string;
  endDate?: string;
  importedOnly?: boolean;
  page?: number;
  pageSize?: number;
}
