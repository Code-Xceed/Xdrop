import React, { useState, useEffect } from 'react';
import { AppSettings, IntegrationsStatus, IntegrationHost, UpdateInfo } from '@xdrop/shared-types';
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
} from 'lucide-react';

interface SettingsPageProps {
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ showToast }) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
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
      setToolsStatus(t);
      setIntegrations(i);
      if (u) setUpdateInfo(u);
    } catch (e: any) {
      showToast(e.message || 'Failed to load configuration', 'error');
    }
  };

  const handleCheckUpdate = async () => {
    setIsCheckingUpdate(true);
    try {
      const res = await checkForUpdates(true);
      setUpdateInfo(res);
      if (res.updateAvailable) {
        showToast(`Update v${res.latestVersion} is available`, 'info');
      } else {
        showToast('Xdrop is up to date', 'success');
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

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSettings(settings);
      showToast('Settings saved successfully', 'success');
      loadSettings();
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
        <p style={{ fontWeight: 500, fontSize: '11px' }}>Loading studio configuration...</p>
      </div>
    );
  }

  const tokens = ['{project}', '{platform}', '{mediaType}', '{date}', '{title}', '{quality}'];

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '14px 14px 40px' }}>
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* 1. Target Editor & Bins */}
        <div className="panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Layers size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              Editor Bins & Auto-Import
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
            {/* Resolve */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  DaVinci Resolve
                </span>
                <span className="badge" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  Media Pool
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Target bin name
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetMediaPoolBin}
                onChange={(e) => setSettings({ ...settings, targetMediaPoolBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import</span>
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

            {/* Premiere Pro */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Adobe Premiere Pro
                </span>
                <span className="badge" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  Project Bin
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Target bin name
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetPremiereBin || 'Xdrop'}
                onChange={(e) => setSettings({ ...settings, targetPremiereBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import</span>
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

            {/* After Effects */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Adobe After Effects
                </span>
                <span className="badge" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  Project Folder
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Target folder name
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetAfterEffectsBin || 'Xdrop'}
                onChange={(e) => setSettings({ ...settings, targetAfterEffectsBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '28px', fontSize: '11px', marginBottom: '10px' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import</span>
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
          </div>
        </div>

        {/* 2. Transcoding & Timeline Optimization */}
        <div className="panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Film size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              Transcoding & Timeline Playback
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                Default Video Codec
              </label>
              <select
                className="input"
                value={settings.preferredVideoFormat}
                onChange={(e) => setSettings({ ...settings, preferredVideoFormat: e.target.value as any })}
                style={{ backgroundColor: 'var(--bg-primary)', height: '30px', fontSize: '11px' }}
              >
                <option value="mp4">Universal MP4 (H.264 / AAC)</option>
                <option value="mov">Apple ProRes 422 (MOV)</option>
                <option value="original">Direct Stream (Original Container)</option>
              </select>
              <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '5px', lineHeight: 1.4 }}>
                Transcodes VP9 and AV1 streams into edit-ready H.264 for instant scrubbing without dropped frames.
              </span>
            </div>

            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                Default Audio Codec
              </label>
              <select
                className="input"
                value={settings.preferredAudioFormat}
                onChange={(e) => setSettings({ ...settings, preferredAudioFormat: e.target.value as any })}
                style={{ backgroundColor: 'var(--bg-primary)', height: '30px', fontSize: '11px' }}
              >
                <option value="wav">WAV (Lossless 24-bit PCM)</option>
                <option value="mp3">MP3 (320 kbps High Quality)</option>
                <option value="aac">AAC (Stereo Native)</option>
              </select>
              <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '5px', lineHeight: 1.4 }}>
                Uncompressed WAV is recommended for timeline editing and audio post-production.
              </span>
            </div>
          </div>
        </div>

        {/* 3. Storage & Naming */}
        <div className="panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Folder size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              Storage Directory & File Naming
            </h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                Local Cache Directory
              </label>
              <input
                type="text"
                className="input"
                value={settings.downloadDir}
                onChange={(e) => setSettings({ ...settings, downloadDir: e.target.value })}
                style={{ backgroundColor: 'var(--bg-primary)', fontFamily: 'var(--font-mono)', height: '30px', fontSize: '11px' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                File Naming Pattern
              </label>
              <input
                type="text"
                className="input"
                value={settings.namingPattern}
                onChange={(e) => setSettings({ ...settings, namingPattern: e.target.value })}
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  fontFamily: 'var(--font-mono)',
                  height: '30px',
                  fontSize: '11px',
                  marginBottom: '8px',
                }}
              />
              <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                {tokens.map((tok) => (
                  <button
                    key={tok}
                    type="button"
                    onClick={() => insertToken(tok)}
                    className="btn btn-sm btn-ghost"
                    style={{
                      fontSize: '9.5px',
                      padding: '2px 7px',
                      fontFamily: 'var(--font-mono)',
                      border: '1px solid var(--border-default)',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    }}
                  >
                    + {tok}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 4. Host Integrations & Bridge Health */}
        <div className="panel">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wrench size={14} strokeWidth={2} color="var(--text-secondary)" />
              <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                Editor Bridges & Add-Ons
              </h4>
            </div>
            <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 6px' }}>
              Local User Install
            </span>
          </div>

          <p style={{ fontSize: '10px', color: 'var(--text-muted)', margin: '0 0 12px', lineHeight: 1.4 }}>
            Integrations register the extension panels and ExtendScript bridges for DaVinci Resolve Studio and Adobe Premiere Pro.
          </p>

          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <button
              type="button"
              onClick={() => handleInstall()}
              disabled={isInstallingAll || installingHost !== null}
              className="btn btn-primary btn-sm"
              style={{ flex: 1, fontSize: '11px', padding: '6px 12px' }}
            >
              {isInstallingAll ? (
                <Loader2 size={12} className="spin" />
              ) : (
                <ShieldCheck size={13} strokeWidth={2} />
              )}
              <span>
                {isInstallingAll
                  ? 'Installing Bridges...'
                  : integrations?.hosts.every((h) => h.installed)
                  ? 'Re-verify All Bridges'
                  : 'Install All Editor Bridges'}
              </span>
            </button>

            <button
              type="button"
              onClick={loadSettings}
              className="btn btn-sm btn-ghost"
              style={{ fontSize: '11px', padding: '6px 12px', gap: '5px', border: '1px solid var(--border-default)' }}
              title="Re-scan editor plugin directories"
            >
              <RefreshCw size={12} strokeWidth={2} />
              <span>Scan</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
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
                    <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 6px', gap: '3px' }}>
                      <CheckCircle2 size={9} strokeWidth={2.5} /> Ready
                    </span>
                  ) : (
                    <span className="badge badge-warning" style={{ fontSize: '9px', padding: '1px 6px', gap: '3px' }}>
                      <AlertCircle size={9} strokeWidth={2.5} /> Not Installed
                    </span>
                  )}
                  {host.requiresAdmin && (
                    <span className="badge badge-danger" style={{ fontSize: '9px', padding: '1px 5px' }}>
                      Needs Admin
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
                    marginTop: '5px',
                    wordBreak: 'break-all',
                  }}
                >
                  {host.path || `Path: ${host.checkedPaths.join(' • ')}`}
                </div>
              </div>
            ))}

            {/* Adobe developer mode status if missing */}
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
                    Adobe Developer Mode Disabled
                  </span>
                </div>
                <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Premiere Pro and After Effects load folder-based panels when developer mode is enabled:
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

            {/* FFmpeg Engine Status */}
            <div
              style={{
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Cpu size={13} strokeWidth={2} color="var(--text-secondary)" />
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                FFmpeg Media Engine
              </span>
              {toolsStatus?.ffmpeg?.isAvailable ? (
                <span className="badge badge-success" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  Hardware Accelerated
                </span>
              ) : (
                <span className="badge badge-danger" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  Offline
                </span>
              )}
              <span
                style={{
                  fontSize: '9.5px',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                  marginLeft: 'auto',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '50%',
                }}
              >
                {toolsStatus?.ffmpeg?.info || 'Ready'}
              </span>
            </div>
          </div>
        </div>

        {/* 5. Updates & System */}
        <div className="panel">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ArrowUpCircle size={14} strokeWidth={2} color="var(--success)" />
              <h4 style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                Updates & Engine Diagnostics
              </h4>
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

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Installed Version</span>
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
                  Latest Build
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
                <strong>v{updateInfo.latestVersion}</strong> is ready to install.
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

        {/* 6. Save Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
          <button
            type="submit"
            disabled={isSaving}
            className="btn btn-primary"
            style={{ padding: '8px 18px', fontSize: '11.5px', gap: '6px' }}
          >
            {isSaving ? <Loader2 size={13} className="spin" /> : <Save size={13} strokeWidth={2} />}
            <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
