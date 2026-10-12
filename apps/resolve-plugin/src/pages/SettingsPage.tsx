import React, { useState, useEffect } from 'react';
import { AppSettings, IntegrationsStatus, IntegrationHost } from '@xdrop/shared-types';
import {
  getSettings,
  updateSettings,
  getToolsStatus,
  getIntegrationsStatus,
  installIntegrations,
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
} from 'lucide-react';

interface SettingsPageProps {
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ showToast }) => {

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [toolsStatus, setToolsStatus] = useState<any>(null);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isInstallingAll, setIsInstallingAll] = useState(false);
  const [installingHost, setInstallingHost] = useState<IntegrationHost | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [s, t, i] = await Promise.all([
        getSettings(),
        getToolsStatus(),
        getIntegrationsStatus(),
      ]);
      setSettings(s);
      setToolsStatus(t);
      setIntegrations(i);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSettings(settings);
      showToast('Settings saved successfully.', 'success');
      loadSettings();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * The one-click path: every host, current user only, so no administrator prompt and no
   * console window. `hosts` narrows it to a single host for the per-host re-install buttons.
   */
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
      showToast(e.message, 'error');
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
        <span className="spin" style={{ display: 'inline-block', fontSize: '18px', marginBottom: '8px' }}>⟳</span>
        <p style={{ fontWeight: 500, fontSize: '11px', letterSpacing: '0.04em' }}>LOADING SETTINGS...</p>
      </div>
    );
  }

  const tokens = ['{project}', '{platform}', '{mediaType}', '{date}', '{title}', '{quality}'];

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '14px 12px' }}>
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* 1. Target Video Editor & Bins */}
        <div className="panel" style={{ backgroundColor: 'var(--bg-secondary)', padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
            <Layers size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Target Editor Bins
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
            {/* Resolve Destination */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  DaVinci Resolve
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Media Pool Bin
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetMediaPoolBin}
                onChange={(e) => setSettings({ ...settings, targetMediaPoolBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '30px', fontSize: '11px' }}
              />
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginTop: '8px', fontSize: '11px' }}>
                <input
                  type="checkbox"
                  checked={settings.autoImportToResolve}
                  onChange={(e) => setSettings({ ...settings, autoImportToResolve: e.target.checked })}
                  style={{ width: '13px', height: '13px', accentColor: '#ffffff' }}
                />
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import after download</span>
              </label>
            </div>

            {/* Premiere Pro Destination */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Adobe Premiere Pro
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Project Panel Bin
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetPremiereBin || 'Xdrop'}
                onChange={(e) => setSettings({ ...settings, targetPremiereBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '30px', fontSize: '11px' }}
              />
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginTop: '8px', fontSize: '11px' }}>
                <input
                  type="checkbox"
                  checked={settings.autoImportToPremiere ?? true}
                  onChange={(e) => setSettings({ ...settings, autoImportToPremiere: e.target.checked })}
                  style={{ width: '13px', height: '13px', accentColor: '#ffffff' }}
                />
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import after download</span>
              </label>
            </div>

            {/* After Effects Destination */}
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Adobe After Effects
                </span>
              </div>
              <label style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Project Panel Bin / Folder
              </label>
              <input
                type="text"
                className="input"
                value={settings.targetAfterEffectsBin || 'Xdrop'}
                onChange={(e) => setSettings({ ...settings, targetAfterEffectsBin: e.target.value })}
                placeholder="Xdrop"
                style={{ backgroundColor: 'var(--bg-primary)', height: '30px', fontSize: '11px' }}
              />
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginTop: '8px', fontSize: '11px' }}>
                <input
                  type="checkbox"
                  checked={settings.autoImportToAfterEffects ?? true}
                  onChange={(e) => setSettings({ ...settings, autoImportToAfterEffects: e.target.checked })}
                  style={{ width: '13px', height: '13px', accentColor: '#ffffff' }}
                />
                <span style={{ color: 'var(--text-secondary)', fontSize: '10.5px' }}>Auto-import after download</span>
              </label>
            </div>
          </div>
        </div>

        {/* 2. NLE Codec & Compatibility Engine */}
        <div className="panel" style={{ backgroundColor: 'var(--bg-secondary)', padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
            <ShieldCheck size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Transcode & Codec Preferences
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
                VIDEO PRESET
              </label>
              <select
                className="input"
                value={settings.preferredVideoFormat}
                onChange={(e) => setSettings({ ...settings, preferredVideoFormat: e.target.value as any })}
                style={{ backgroundColor: 'var(--bg-primary)', height: '32px', fontSize: '11px' }}
              >
                <option value="mp4">Universal MP4 (H.264 / AAC)</option>
                <option value="mov">Apple ProRes 422 (MOV)</option>
                <option value="original">Original Stream Format</option>
              </select>
              <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
                Transcodes AV1/VP9 to H.264 for crash-free timeline playback across all NLEs.
              </span>
            </div>

            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
                AUDIO FORMAT
              </label>
              <select
                className="input"
                value={settings.preferredAudioFormat}
                onChange={(e) => setSettings({ ...settings, preferredAudioFormat: e.target.value as any })}
                style={{ backgroundColor: 'var(--bg-primary)', height: '32px', fontSize: '11px' }}
              >
                <option value="wav">WAV (Lossless 24-bit PCM)</option>
                <option value="mp3">MP3 (320 kbps High Bitrate)</option>
                <option value="aac">AAC (Stereo)</option>
              </select>
            </div>
          </div>
        </div>

        {/* 3. Storage & Naming Pattern */}
        <div className="panel" style={{ backgroundColor: 'var(--bg-secondary)', padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
            <Folder size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Storage & Naming
            </h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
                DOWNLOAD DIRECTORY
              </label>
              <input
                type="text"
                className="input"
                value={settings.downloadDir}
                onChange={(e) => setSettings({ ...settings, downloadDir: e.target.value })}
                style={{ backgroundColor: 'var(--bg-primary)', fontFamily: 'var(--font-mono)', height: '32px', fontSize: '11px' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>
                NAMING TEMPLATE
              </label>
              <input
                type="text"
                className="input"
                value={settings.namingPattern}
                onChange={(e) => setSettings({ ...settings, namingPattern: e.target.value })}
                style={{ backgroundColor: 'var(--bg-primary)', fontFamily: 'var(--font-mono)', height: '32px', fontSize: '11px', marginBottom: '6px' }}
              />
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {tokens.map((tok) => (
                  <button
                    key={tok}
                    type="button"
                    onClick={() => insertToken(tok)}
                    className="btn btn-sm btn-ghost"
                    style={{
                      fontSize: '9.5px',
                      padding: '2px 6px',
                      fontFamily: 'var(--font-mono)',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    + {tok}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 4. Editor Integrations — one click, per-user, no admin, no console window */}
        <div className="panel" style={{ backgroundColor: 'var(--bg-secondary)', padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <Wrench size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Editor Integrations
            </h4>
            <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 5px', marginLeft: 'auto' }}>
              NO ADMIN NEEDED
            </span>
          </div>
          <p style={{ fontSize: '10px', color: 'var(--text-muted)', margin: '0 0 10px' }}>
            Installs into this user's own editor folders and enables Adobe developer mode
            silently — nothing to run, no password prompt.
          </p>

          <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
            <button
              type="button"
              onClick={() => handleInstall()}
              disabled={isInstallingAll || installingHost !== null}
              className="btn btn-primary btn-sm"
              style={{ flex: 1, fontSize: '10.5px', padding: '6px 10px' }}
            >
              <ShieldCheck size={12} strokeWidth={2} />
              <span>
                {isInstallingAll
                  ? 'Installing everything...'
                  : integrations?.hosts.every((h) => h.installed)
                  ? 'Re-install all integrations'
                  : 'Install all integrations'}
              </span>
            </button>
            <button
              type="button"
              onClick={loadSettings}
              className="btn btn-sm btn-ghost"
              style={{ fontSize: '10.5px', padding: '6px 10px' }}
              title="Re-scan every editor folder"
            >
              <RefreshCw size={12} strokeWidth={2} />
              <span>Re-scan</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {integrations?.hosts.map((host) => (
              <div
                key={host.host}
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {host.label}
                  </span>
                  {host.installed ? (
                    <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 5px', gap: '3px' }}>
                      <CheckCircle2 size={9} strokeWidth={2.5} /> READY
                    </span>
                  ) : (
                    <span className="badge badge-warning" style={{ fontSize: '8.5px', padding: '1px 5px', gap: '3px' }}>
                      <AlertCircle size={9} strokeWidth={2.5} /> NOT INSTALLED
                    </span>
                  )}
                  {host.requiresAdmin && (
                    <span className="badge badge-danger" style={{ fontSize: '8.5px', padding: '1px 5px' }}>
                      NEEDS ADMIN
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => handleInstall([host.host])}
                    disabled={isInstallingAll || installingHost === host.host}
                    className="btn btn-sm btn-ghost"
                    style={{ marginLeft: 'auto', fontSize: '9.5px', padding: '3px 8px' }}
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
                  {host.path || `Not found in: ${host.checkedPaths.join(' • ')}`}
                </div>

                {host.notes.map((note) => (
                  <div key={note} style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {note}
                  </div>
                ))}
              </div>
            ))}

            {/* Adobe developer mode is what makes an unsigned panel visible at all. If it is
                off, show the exact command instead of telling the user to "check the registry". */}
            {integrations?.cepSupported && integrations.playerDebugMode.missing.length > 0 && (
              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={12} strokeWidth={2} color="var(--danger)" />
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Adobe developer mode is off
                  </span>
                </div>
                <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '5px' }}>
                  Premiere Pro and After Effects only list a folder-installed panel when
                  developer mode is on. Re-installing enables it; to do it by hand:
                </div>
                <div
                  style={{
                    fontSize: '9px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    marginTop: '5px',
                    wordBreak: 'break-all',
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
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
                FFmpeg HW Engine
              </span>
              {toolsStatus?.ffmpeg?.isAvailable ? (
                <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 4px' }}>ACTIVE</span>
              ) : (
                <span className="badge badge-danger" style={{ fontSize: '8.5px', padding: '1px 4px' }}>OFFLINE</span>
              )}
              <span
                style={{
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                  marginLeft: 'auto',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '55%',
                }}
              >
                {toolsStatus?.ffmpeg?.info || 'Hardware Acceleration Engine'}
              </span>
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            type="submit"
            disabled={isSaving}
            className="btn btn-primary"
            style={{ padding: '7px 16px', fontSize: '11.5px' }}
          >
            <Save size={13} strokeWidth={2} />
            <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
