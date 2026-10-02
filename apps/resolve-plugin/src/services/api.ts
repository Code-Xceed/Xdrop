import {
  MediaInfo,
  DownloadJob,
  ResolveStatus,
  PremiereStatus,
  AfterEffectsStatus,
  EditorsStatus,
  SupportedEditor,
  AppSettings,
  LibraryItem,
  LibraryFilter,
} from '@xdrop/shared-types';

const API_BASE = '/api';

export interface CreateDownloadParams {
  source_url: string;
  asset_id?: string;
  format?: string;
  quality_label?: string;
  media_type?: string;
  title?: string;
  author?: string;
  target_media_pool_bin?: string;
  auto_import_to_resolve?: boolean;
  target_editor?: SupportedEditor | 'auto';
  auto_import_to_premiere?: boolean;
  target_premiere_bin?: string;
  auto_import_to_aftereffects?: boolean;
  target_aftereffects_bin?: string;
  transcode_video_format?: string;
  transcode_audio_format?: string;
  extract_audio_only?: boolean;
  generate_proxy?: boolean;
}

export async function analyzeUrl(url: string): Promise<MediaInfo> {
  const resp = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Analysis failed with status ${resp.status}`);
  }
  const data = await resp.json();
  return {
    url: data.url,
    platform: data.platform,
    platformName: data.platformName || data.platform_name || data.platform,
    title: data.title,
    author: data.author,
    authorUrl: data.authorUrl || data.author_url,
    sourceId: data.sourceId || data.source_id,
    duration: data.duration,
    thumbnailUrl: data.thumbnailUrl || data.thumbnail_url,
    description: data.description,
    assets: (data.assets || []).map((a: any) => ({
      id: a.id,
      mediaType: a.mediaType || a.media_type || 'video',
      format: a.format || 'mp4',
      qualityLabel: a.qualityLabel || a.quality_label || (a.format ? a.format.toUpperCase() : 'Standard'),
      resolution: a.resolution,
      fps: a.fps,
      vcodec: a.vcodec,
      acodec: a.acodec,
      filesizeApprox: a.filesizeApprox ?? a.filesize_approx,
      url: a.url,
      isDefault: Boolean(a.isDefault ?? a.is_default),
    })),
  };
}

export async function analyzeBatchUrls(urls: string[]): Promise<{ detected: Array<{ url: string; supported: boolean; platform: string; platformName: string }>; total: number }> {
  const resp = await fetch(`${API_BASE}/analyze/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls }),
  });
  if (!resp.ok) {
    throw new Error('Batch URL analysis failed.');
  }
  return resp.json();
}

export async function createDownload(params: CreateDownloadParams): Promise<DownloadJob> {
  const resp = await fetch(`${API_BASE}/downloads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start download.');
  }
  return resp.json();
}

export async function listDownloads(): Promise<DownloadJob[]> {
  const resp = await fetch(`${API_BASE}/downloads`);
  if (!resp.ok) throw new Error('Failed to fetch downloads queue.');
  return resp.json();
}

export async function cancelDownload(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/downloads/${id}/cancel`, { method: 'POST' });
  if (!resp.ok) throw new Error('Failed to cancel download.');
}

export async function retryDownload(id: string): Promise<DownloadJob> {
  const resp = await fetch(`${API_BASE}/downloads/${id}/retry`, { method: 'POST' });
  if (!resp.ok) throw new Error('Failed to retry download.');
  return resp.json();
}

export async function removeDownload(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/downloads/${id}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error('Failed to remove download.');
}

export async function importJobToResolve(id: string): Promise<{ success: boolean; clipName?: string; error?: string }> {
  const resp = await fetch(`${API_BASE}/downloads/${id}/import`, { method: 'POST' });
  return resp.json();
}

export async function getLibrary(filters: LibraryFilter = {}): Promise<{ items: LibraryItem[]; count: number }> {
  const params = new URLSearchParams();
  if (filters.search) params.append('search', filters.search);
  if (filters.platform) params.append('platform', filters.platform);
  if (filters.mediaType) params.append('media_type', filters.mediaType);
  if (filters.importedOnly !== undefined) params.append('resolve_imported', String(filters.importedOnly));
  if (filters.page && filters.pageSize) {
    params.append('limit', String(filters.pageSize));
    params.append('offset', String((filters.page - 1) * filters.pageSize));
  }

  const resp = await fetch(`${API_BASE}/library?${params.toString()}`);
  if (!resp.ok) throw new Error('Failed to fetch library.');
  return resp.json();
}

export async function deleteLibraryItem(id: string, deleteFile = false): Promise<void> {
  const resp = await fetch(`${API_BASE}/library/${id}?delete_file=${deleteFile}`, {
    method: 'DELETE',
  });
  if (!resp.ok) throw new Error('Failed to delete asset.');
}

export async function importLibraryItem(id: string): Promise<{ success: boolean; clipName?: string; error?: string }> {
  const resp = await fetch(`${API_BASE}/library/${id}/import`, { method: 'POST' });
  return resp.json();
}

export async function importLibraryItemToPremiere(id: string): Promise<{ success: boolean; error?: string }> {
  const resp = await fetch(`${API_BASE}/library/${id}/import-premiere`, { method: 'POST' });
  return resp.json();
}

export async function importLibraryItemToAfterEffects(id: string): Promise<{ success: boolean; error?: string }> {
  const resp = await fetch(`${API_BASE}/library/${id}/import-aftereffects`, { method: 'POST' });
  return resp.json();
}

export async function revealLibraryItem(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/library/${id}/reveal`, { method: 'POST' });
  if (!resp.ok) throw new Error('Failed to reveal file in explorer.');
}

export async function getSettings(): Promise<AppSettings> {
  const resp = await fetch(`${API_BASE}/settings`);
  if (!resp.ok) throw new Error('Failed to fetch settings.');
  return resp.json();
}

export async function updateSettings(settings: Partial<AppSettings>): Promise<{ success: boolean; settings: AppSettings }> {
  const resp = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!resp.ok) throw new Error('Failed to update settings.');
  return resp.json();
}

export async function getToolsStatus(): Promise<{
  ffmpeg: { isAvailable: boolean; path: string; info: string };
  resolveScript: { isInstalled: boolean };
  premiereExtension?: { isInstalled: boolean };
  aftereffectsExtension?: { isInstalled: boolean };
}> {
  const resp = await fetch(`${API_BASE}/settings/tools-status`);
  if (!resp.ok) throw new Error('Failed to get tools status.');
  return resp.json();
}

export async function installResolveScript(): Promise<{ success: boolean; message: string }> {
  const resp = await fetch(`${API_BASE}/settings/install-resolve-script`, { method: 'POST' });
  return resp.json();
}

export async function installPremiereExtension(): Promise<{ success: boolean; message: string }> {
  const resp = await fetch(`${API_BASE}/settings/install-premiere-extension`, { method: 'POST' });
  return resp.json();
}

export async function installAfterEffectsExtension(): Promise<{ success: boolean; message: string }> {
  const resp = await fetch(`${API_BASE}/settings/install-aftereffects-extension`, { method: 'POST' });
  return resp.json();
}

export async function getResolveStatus(): Promise<ResolveStatus> {
  const resp = await fetch(`${API_BASE}/resolve/status`);
  if (!resp.ok) throw new Error('Failed to get Resolve status.');
  return resp.json();
}

export async function getPremiereStatus(): Promise<PremiereStatus> {
  const resp = await fetch(`${API_BASE}/premiere/status`);
  if (!resp.ok) throw new Error('Failed to get Premiere status.');
  return resp.json();
}

export async function getAfterEffectsStatus(): Promise<AfterEffectsStatus> {
  const resp = await fetch(`${API_BASE}/aftereffects/status`);
  if (!resp.ok) throw new Error('Failed to get After Effects status.');
  return resp.json();
}

export async function getEditorsStatus(): Promise<EditorsStatus> {
  const resp = await fetch(`${API_BASE}/editors/status`);
  if (!resp.ok) throw new Error('Failed to get editors status.');
  return resp.json();
}

export async function importJobToPremiere(id: string): Promise<{ success: boolean; clipName?: string; error?: string }> {
  const resp = await fetch(`${API_BASE}/downloads/${id}/import-premiere`, { method: 'POST' });
  return resp.json();
}

export async function importJobToAfterEffects(id: string): Promise<{ success: boolean; clipName?: string; error?: string }> {
  const resp = await fetch(`${API_BASE}/downloads/${id}/import-aftereffects`, { method: 'POST' });
  return resp.json();
}
