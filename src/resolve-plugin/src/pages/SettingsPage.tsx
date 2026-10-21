import React, { useState, useEffect } from 'react';
import { AppSettings, IntegrationsStatus, IntegrationHost, UpdateInfo } from '@xdrop/shared-types';
import { useEditorContext } from '../context/EditorContext';
import {
  getSettings,
  updateSettings,
  getToolsStatus,
  getIntegrationsStatus,
  installIntegrations,
  checkForUpdates,
  installUpdate,
} from '../services/api';
import {
  Folder,
  Layers,
  Wrench,
  Save,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowUpCircle,
  Film,
  Loader2,
  Cpu,
  Eye,
} from 'lucide-react';

interface SettingsPageProps {
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

type SettingsTab = 'bins' | 'codecs' | 'storage' | 'system';

export const SettingsPage: React.FC<SettingsPageProps> = ({ showToast }) => {
  const { activeEditor } = useEditorContext();
  const [activeTab, setActiveTab] = useState<SettingsTab>('bins');
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [initialSettings, setInitialSettings] = useState<string>('');
  const [toolsStatus, setToolsStatus] = useState<any>(null);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isCheckingUpdate, setIsCheckingUpdate] = useState(false);
  const [isInstallingUpdate, setIsInstallingUpdate] = useState(false);
  const [isInstallingAll, setIsInstallingAll] = useState(false);
  const [installingHost, setInstallingHost] = useState<IntegrationHost | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [s, t, i, u] = await Promise.all([
        getSettings(),
        getToolsStatus(),
        getIntegrationsStatus(),
        checkForUpdates(false).catch(() => null),
      ]);
      setSettings(s);
      setInitialSettings(JSON.stringify(s));
      setToolsStatus(t);
      setIntegrations(i);
      if (u) setUpdateInfo(u);
    } catch (e: any) {
      showToast(e.message || 'Failed to load configuration', 'error');
    }
  };

  const hasUnsavedChanges = settings ? JSON.stringify(settings) !== initialSettings : false;

  const handleCheckUpdate = async () => {
    setIsCheckingUpdate(true);
    try {
      const res = await checkForUpdates(true);
      setUpdateInfo(res);
      if (res.updateAvailable) {
        showToast(`Update v${res.latestVersion} is available`, 'info');
      } else {
        showToast('Xdrop is fully up to date', 'success');
      }
    } catch (e: any) {
      showToast('Could not check for updates', 'error');
    } finally {
      setIsCheckingUpdate(false);
    }
  };

  const handleInstallUpdate = async () => {
    setIsInstallingUpdate(true);
    try {
      await installUpdate(updateInfo?.downloadUrl);
      showToast('Downloading and installing update...', 'info');
    } catch (e: any) {
      setIsInstallingUpdate(false);
      showToast(e.message || 'Could not initiate update', 'error');
    }
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSettings(settings);
      setInitialSettings(JSON.stringify(settings));
      showToast('Settings saved successfully', 'success');
    } catch (e: any) {
      showToast(e.message || 'Failed to save settings', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleInstall = async (hosts?: IntegrationHost[]) => {
    if (hosts?.length === 1) {
      setInstallingHost(hosts[0]);
    } else {
      setIsInstallingAll(true);
    }
    try {
      const res = await installIntegrations(hosts?.length ? { hosts } : undefined);
      setIntegrations(res.status);
      showToast(res.message, res.success ? 'success' : 'error');
    } catch (e: any) {
      showToast(e.message || 'Installation error', 'error');
    } finally {
      setIsInstallingAll(false);
      setInstallingHost(null);
    }
  };

  const insertToken = (token: string) => {
    if (!settings) return;
    setSettings({
      ...settings,
      namingPattern: `${settings.namingPattern}/${token}`,
    });
  };

  if (!settings) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Loader2 size={18} className="spin" style={{ margin: '0 auto 8px', display: 'block' }} />
        <p style={{ fontWeight: 500, fontSize: '11px' }}>Loading configuration...</p>
      </div>
    );
  }

  const tokens = ['{project}', '{platform}', '{mediaType}', '{date}', '{title}', '{quality}'];

  // Example filename preview computed from the template
  const computeFilenamePreview = (pattern: string) => {
    return pattern
      .replace('{project}', 'Project_One')
      .replace('{platform}', 'YouTube')
      .replace('{mediaType}', 'video')
      .replace('{date}', '2026-10-20')
      .replace('{title}', 'Cinematic_Sample')
      .replace('{quality}', '2160p');
  };

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '12px 14px 60px' }}>
      {/* Settings Category Navigation & Save Action */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '14px',
          flexWrap: 'wrap',
        }}
      >
        {/* Segmented Category Control */}
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
              { id: 'bins', label: 'Editor Bins', icon: Layers },
              { id: 'codecs', label: 'Timeline Codecs', icon: Film },
              { id: 'storage', label: 'Storage & Naming', icon: Folder },
              { id: 'system', label: 'Bridges & System', icon: Wrench },
            ] as const
          ).map((tab) => {
            const isSel = activeTab === tab.id;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                style={{
                  border: isSel ? '1px solid var(--border-strong)' : '1px solid transparent',
                  backgroundColor: isSel ? 'var(--bg-elevated)' : 'transparent',
                  color: isSel ? '#ffffff' : 'var(--text-muted)',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-pill)',
                  fontSize: '10.5px',
                  fontWeight: isSel ? 600 : 500,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  transition: 'all 120ms ease',
                  boxShadow: isSel ? '0 1px 2px rgba(0,0,0,0.4)' : 'none',
                }}
              >
                <Icon size={12} strokeWidth={isSel ? 2.2 : 1.8} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Quick Save Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {hasUnsavedChanges && (
            <span style={{ fontSize: '10px', color: 'var(--warning)', fontWeight: 500 }}>
              Unsaved changes
            </span>
          )}
          <button
            type="button"
            onClick={() => handleSave()}
            disabled={isSaving || !hasUnsavedChanges}
            className="btn btn-sm btn-primary"
            style={{
              padding: '4px 12px',
              fontSize: '11px',
              gap: '5px',
              opacity: hasUnsavedChanges ? 1 : 0.6,
            }}
          >
            {isSaving ? <Loader2 size={12} className="spin" /> : <Save size={12} strokeWidth={2} />}
            <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSave}>
        {/* =========================================================================
            TAB 1: EDITOR BINS & WORKFLOW
            ========================================================================= */}
        {activeTab === 'bins' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="panel">
              <div style={{ marginBottom: '12px' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  Target Workspace Bins
                </h4>
                <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Configure the project bins where downloaded media will automatically register.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '10px' }}>
                {/* Adobe Premiere Pro */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: `1px solid ${activeEditor === 'premiere' ? 'rgba(56, 189, 248, 0.4)' : 'var(--border-default)'}`,
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Adobe Premiere Pro
                    </span>
                    {activeEditor === 'premiere' ? (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
                        Active Host
                      </span>
                    ) : (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                        Project Bin
                      </span>
                    )}
                  </div>
                  <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Project panel bin name
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={settings.targetPremiereBin || 'Xdrop'}
                    onChange={(e) => setSettings({ ...settings, targetPremiereBin: e.target.value })}
                    placeholder="Xdrop"
                    style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
                  />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '2px' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import to project</span>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={settings.autoImportToPremiere ?? true}
                        onChange={(e) => setSettings({ ...settings, autoImportToPremiere: e.target.checked })}
                      />
                      <span className="slider" />
                    </label>
                  </div>
                </div>

                {/* DaVinci Resolve */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: `1px solid ${activeEditor === 'resolve' ? 'rgba(52, 211, 153, 0.4)' : 'var(--border-default)'}`,
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      DaVinci Resolve
                    </span>
                    {activeEditor === 'resolve' ? (
                      <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                        Active Host
                      </span>
                    ) : (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                        Media Pool
                      </span>
                    )}
                  </div>
                  <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Media Pool target bin
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={settings.targetMediaPoolBin}
                    onChange={(e) => setSettings({ ...settings, targetMediaPoolBin: e.target.value })}
                    placeholder="Xdrop"
                    style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
                  />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '2px' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import to Media Pool</span>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={settings.autoImportToResolve}
                        onChange={(e) => setSettings({ ...settings, autoImportToResolve: e.target.checked })}
                      />
                      <span className="slider" />
                    </label>
                  </div>
                </div>

                {/* Adobe After Effects */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: `1px solid ${activeEditor === 'aftereffects' ? 'rgba(168, 85, 247, 0.4)' : 'var(--border-default)'}`,
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Adobe After Effects
                    </span>
                    {activeEditor === 'aftereffects' ? (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px', backgroundColor: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
                        Active Host
                      </span>
                    ) : (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                        Project Folder
                      </span>
                    )}
                  </div>
                  <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Project panel folder name
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={settings.targetAfterEffectsBin || 'Xdrop'}
                    onChange={(e) => setSettings({ ...settings, targetAfterEffectsBin: e.target.value })}
                    placeholder="Xdrop"
                    style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
                  />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '2px' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import to project</span>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={settings.autoImportToAfterEffects ?? true}
                        onChange={(e) => setSettings({ ...settings, autoImportToAfterEffects: e.target.checked })}
                      />
                      <span className="slider" />
                    </label>
                  </div>
                </div>

                {/* Adobe Audition */}
                <div
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: `1px solid ${activeEditor === 'audition' ? 'rgba(56, 189, 248, 0.4)' : 'var(--border-default)'}`,
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Adobe Audition
                    </span>
                    {activeEditor === 'audition' ? (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
                        Active Host
                      </span>
                    ) : (
                      <span className="badge" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                        Session Bin
                      </span>
                    )}
                  </div>
                  <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Session target folder
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={(settings as any).targetAuditionBin || 'Xdrop'}
                    onChange={(e) => setSettings({ ...settings, targetAuditionBin: e.target.value } as any)}
                    placeholder="Xdrop"
                    style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
                  />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '2px' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import audio tracks</span>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={(settings as any).autoImportToAudition ?? true}
                        onChange={(e) => setSettings({ ...settings, autoImportToAudition: e.target.checked } as any)}
                      />
                      <span className="slider" />
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 2: TIMELINE CODECS & TRANSCODING
            ========================================================================= */}
        {activeTab === 'codecs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="panel">
              <div style={{ marginBottom: '12px' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  Default Playback Codecs
                </h4>
                <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Xdrop converts non-native web codecs (VP9, AV1, Opus) to editor-optimized containers for smooth scrubbing.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                    Video Format
                  </label>
                  <select
                    className="input"
                    value={settings.preferredVideoFormat}
                    onChange={(e) => setSettings({ ...settings, preferredVideoFormat: e.target.value as any })}
                    style={{ backgroundColor: 'var(--bg-primary)', height: '32px', fontSize: '11px' }}
                  >
                    <option value="mp4">Universal MP4 (H.264 / AAC) — Best Compatibility</option>
                    <option value="mov">Apple ProRes 422 (MOV) — Post-Production Master</option>
                    <option value="original">Direct Stream Container — Fast, No Re-encode</option>
                  </select>
                  <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '6px', lineHeight: 1.4 }}>
                    Universal MP4 offers hardware decoding across Windows, macOS, and Linux timelines.
                  </span>
                </div>

                <div>
                  <label style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                    Audio Format
                  </label>
                  <select
                    className="input"
                    value={settings.preferredAudioFormat}
                    onChange={(e) => setSettings({ ...settings, preferredAudioFormat: e.target.value as any })}
                    style={{ backgroundColor: 'var(--bg-primary)', height: '32px', fontSize: '11px' }}
                  >
                    <option value="wav">WAV (Lossless 24-bit PCM) — Timeline Recommended</option>
                    <option value="mp3">MP3 (320 kbps High Bitrate)</option>
                    <option value="aac">AAC (Stereo Native)</option>
                  </select>
                  <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '6px', lineHeight: 1.4 }}>
                    Lossless WAV eliminates decoding overhead during waveform rendering.
                  </span>
                </div>
              </div>
            </div>

            {/* Performance & Concurrency */}
            <div className="panel">
              <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>
                Download Performance
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                    Concurrent Transfers: {settings.concurrentDownloads || 3}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="6"
                    value={settings.concurrentDownloads || 3}
                    onChange={(e) => setSettings({ ...settings, concurrentDownloads: parseInt(e.target.value, 10) })}
                    style={{ width: '100%', accentColor: '#ffffff' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    <span>1 (Conservative)</span>
                    <span>3 (Balanced)</span>
                    <span>6 (High Speed)</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0' }}>
                  <div>
                    <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-primary)', display: 'block' }}>
                      Overwrite Existing Files
                    </span>
                    <span style={{ fontSize: '9.5px', color: 'var(--text-muted)' }}>
                      Re-download assets even if cached locally
                    </span>
                  </div>
                  <label className="switch">
                    <input
                      type="checkbox"
                      checked={settings.overwriteExisting || false}
                      onChange={(e) => setSettings({ ...settings, overwriteExisting: e.target.checked })}
                    />
                    <span className="slider" />
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 3: STORAGE & FILE NAMING
            ========================================================================= */}
        {activeTab === 'storage' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="panel">
              <div style={{ marginBottom: '12px' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  Local Storage Directory
                </h4>
                <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  The root destination folder on your machine where media streams are saved.
                </p>
              </div>

              <input
                type="text"
                className="input"
                value={settings.downloadDir}
                onChange={(e) => setSettings({ ...settings, downloadDir: e.target.value })}
                style={{ backgroundColor: 'var(--bg-primary)', fontFamily: 'var(--font-mono)', height: '32px', fontSize: '11px' }}
              />
            </div>

            <div className="panel">
              <div style={{ marginBottom: '10px' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  File Naming Pattern
                </h4>
                <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Construct custom folders and filenames dynamically using metadata tags.
                </p>
              </div>

              <input
                type="text"
                className="input"
                value={settings.namingPattern}
                onChange={(e) => setSettings({ ...settings, namingPattern: e.target.value })}
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  fontFamily: 'var(--font-mono)',
                  height: '32px',
                  fontSize: '11px',
                  marginBottom: '8px',
                }}
              />

              <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginBottom: '12px' }}>
                {tokens.map((tok) => (
                  <button
                    key={tok}
                    type="button"
                    onClick={() => insertToken(tok)}
                    className="btn btn-sm btn-ghost"
                    style={{
                      fontSize: '9.5px',
                      padding: '2px 8px',
                      fontFamily: 'var(--font-mono)',
                      border: '1px solid var(--border-default)',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    }}
                  >
                    + {tok}
                  </button>
                ))}
              </div>

              {/* Dynamic Filename Preview */}
              <div
                style={{
                  padding: '8px 10px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Eye size={12} color="var(--text-muted)" />
                <span style={{ fontSize: '9.5px', color: 'var(--text-muted)' }}>Preview:</span>
                <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {computeFilenamePreview(settings.namingPattern)}.mp4
                </span>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 4: BRIDGES & SYSTEM DIAGNOSTICS
            ========================================================================= */}
        {activeTab === 'system' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Host Bridges */}
            <div className="panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div>
                  <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                    Editor Bridges & Add-Ons
                  </h4>
                  <p style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Extensions that connect Xdrop to DaVinci Resolve, Premiere Pro, and After Effects.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    type="button"
                    onClick={() => handleInstall()}
                    disabled={isInstallingAll || installingHost !== null}
                    className="btn btn-primary btn-sm"
                    style={{ fontSize: '10.5px', padding: '4px 10px', gap: '4px' }}
                  >
                    {isInstallingAll ? <Loader2 size={11} className="spin" /> : <ShieldCheck size={11} strokeWidth={2} />}
                    <span>{isInstallingAll ? 'Installing...' : 'Re-verify All'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={loadSettings}
                    className="btn btn-sm btn-ghost"
                    style={{ fontSize: '10.5px', padding: '4px 8px', border: '1px solid var(--border-default)' }}
                    title="Scan host directories"
                  >
                    <RefreshCw size={11} strokeWidth={2} />
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
                {integrations?.hosts.map((host) => (
                  <div
                    key={host.host}
                    style={{
                      padding: '9px 12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {host.label}
                      </span>
                      {host.installed ? (
                        <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 5px', gap: '3px' }}>
                          <CheckCircle2 size={9} strokeWidth={2.5} /> Ready
                        </span>
                      ) : (
                        <span className="badge badge-warning" style={{ fontSize: '8.5px', padding: '1px 5px', gap: '3px' }}>
                          <AlertCircle size={9} strokeWidth={2.5} /> Not Installed
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleInstall([host.host])}
                        disabled={isInstallingAll || installingHost === host.host}
                        className="btn btn-sm btn-ghost"
                        style={{ marginLeft: 'auto', fontSize: '9.5px', padding: '2px 8px', border: '1px solid var(--border-subtle)' }}
                      >
                        {installingHost === host.host ? 'Installing...' : host.installed ? 'Re-install' : 'Install'}
                      </button>
                    </div>

                    <div
                      style={{
                        fontSize: '9.5px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        marginTop: '4px',
                        wordBreak: 'break-all',
                      }}
                    >
                      {host.path || `Default: ${host.checkedPaths[0] || 'User directory'}`}
                    </div>
                  </div>
                ))}

                {/* Adobe Developer Mode Notice */}
                {integrations?.cepSupported && integrations.playerDebugMode.missing.length > 0 && (
                  <div
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'rgba(251, 191, 36, 0.05)',
                      border: '1px solid rgba(251, 191, 36, 0.25)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertCircle size={12} strokeWidth={2} color="var(--warning)" />
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        Adobe Developer Mode
                      </span>
                    </div>
                    <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Premiere Pro loads custom folder panels when developer mode is enabled:
                    </div>
                    <div
                      style={{
                        fontSize: '9px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-secondary)',
                        marginTop: '4px',
                        wordBreak: 'break-all',
                        backgroundColor: 'var(--bg-primary)',
                        padding: '4px 6px',
                        borderRadius: 'var(--radius-xs)',
                      }}
                    >
                      {integrations.platform === 'macos'
                        ? `defaults write com.adobe.CSXS.${integrations.playerDebugMode.missing[0]} PlayerDebugMode 1`
                        : `reg add HKCU\\Software\\Adobe\\CSXS.${integrations.playerDebugMode.missing[0]} /v PlayerDebugMode /t REG_SZ /d 1 /f`}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Media Processing Engine */}
            <div className="panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Cpu size={14} strokeWidth={2} color="var(--text-secondary)" />
                  <div>
                    <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      FFmpeg Transcoding Engine
                    </span>
                    <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '1px' }}>
                      {toolsStatus?.ffmpeg?.info || 'Hardware Accelerated'}
                    </span>
                  </div>
                </div>

                {toolsStatus?.ffmpeg?.isAvailable ? (
                  <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 6px' }}>
                    Active
                  </span>
                ) : (
                  <span className="badge badge-danger" style={{ fontSize: '9px', padding: '1px 6px' }}>
                    Offline
                  </span>
                )}
              </div>
            </div>

            {/* Software Version & Updates */}
            <div className="panel">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ArrowUpCircle size={14} strokeWidth={2} color="var(--success)" />
                  <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Software Updates
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleCheckUpdate}
                  disabled={isCheckingUpdate}
                  className="btn btn-sm btn-ghost"
                  style={{ fontSize: '10px', padding: '3px 8px', gap: '4px', border: '1px solid var(--border-default)' }}
                >
                  <RefreshCw size={11} className={isCheckingUpdate ? 'spin' : ''} />
                  <span>{isCheckingUpdate ? 'Checking...' : 'Check for Updates'}</span>
                </button>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Installed Build</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    v{updateInfo?.currentVersion || '1.2.1'}
                  </span>
                  {updateInfo?.updateAvailable ? (
                    <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 6px' }}>
                      v{updateInfo.latestVersion} Available
                    </span>
                  ) : (
                    <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '1px 6px' }}>
                      Up to Date
                    </span>
                  )}
                </div>
              </div>

              {updateInfo?.updateAvailable && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(52, 211, 153, 0.08)',
                    border: '1px solid rgba(52, 211, 153, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--text-primary)' }}>
                    <strong>v{updateInfo.latestVersion}</strong> is available.
                    {updateInfo.changelog && (
                      <div style={{ fontSize: '9.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {updateInfo.changelog}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleInstallUpdate}
                    disabled={isInstallingUpdate}
                    className="btn btn-primary btn-sm"
                    style={{ padding: '5px 12px', fontSize: '10.5px' }}
                  >
                    {isInstallingUpdate ? 'Installing...' : 'Install Update'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </form>
    </div>
  );
};
