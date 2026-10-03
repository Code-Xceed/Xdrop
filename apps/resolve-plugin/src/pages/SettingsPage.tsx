import React, { useState, useEffect } from 'react';
import { AppSettings } from '@xdrop/shared-types';
import {
  getSettings,
  updateSettings,
  getToolsStatus,
  installResolveScript,
  installPremiereExtension,
} from '../services/api';
import {
  Folder,
  Layers,
  Wrench,
  Save,
  ShieldCheck,
} from 'lucide-react';

interface SettingsPageProps {
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ showToast }) => {

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [toolsStatus, setToolsStatus] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isInstallingScript, setIsInstallingScript] = useState(false);
  const [isInstallingPremiereExt, setIsInstallingPremiereExt] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [s, t] = await Promise.all([getSettings(), getToolsStatus()]);
      setSettings(s);
      setToolsStatus(t);
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

  const handleInstallResolveScript = async () => {
    setIsInstallingScript(true);
    try {
      const res = await installResolveScript();
      showToast(res.message, 'success');
      loadSettings();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setIsInstallingScript(false);
    }
  };

  const handleInstallPremiereExtension = async () => {
    setIsInstallingPremiereExt(true);
    try {
      const res = await installPremiereExtension();
      showToast(res.message, 'success');
      loadSettings();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setIsInstallingPremiereExt(false);
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

        {/* 4. Integration Diagnostics */}
        <div className="panel" style={{ backgroundColor: 'var(--bg-secondary)', padding: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
            <Wrench size={14} strokeWidth={2} color="var(--text-secondary)" />
            <h4 style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Diagnostics & Integrations
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
            {/* Resolve Script Status */}
            <div style={{ padding: '10px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-default)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>Resolve Script</span>
                {toolsStatus?.resolveScript?.isInstalled ? (
                  <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 4px' }}>READY</span>
                ) : (
                  <span className="badge badge-warning" style={{ fontSize: '8.5px', padding: '1px 4px' }}>MISSING</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleInstallResolveScript}
                disabled={isInstallingScript}
                className="btn btn-sm btn-secondary"
                style={{ width: '100%', fontSize: '10px', padding: '4px 8px' }}
              >
                {isInstallingScript ? 'Installing...' : 'Re-install Script'}
              </button>
            </div>

            {/* Premiere & AE Extension Status */}
            <div style={{ padding: '10px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-default)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>Premiere & AE (CEP)</span>
                {toolsStatus?.premiereExtension?.isInstalled ? (
                  <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 4px' }}>READY</span>
                ) : (
                  <span className="badge badge-warning" style={{ fontSize: '8.5px', padding: '1px 4px' }}>MISSING</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleInstallPremiereExtension}
                disabled={isInstallingPremiereExt}
                className="btn btn-sm btn-secondary"
                style={{ width: '100%', fontSize: '10px', padding: '4px 8px' }}
              >
                {isInstallingPremiereExt ? 'Syncing...' : 'Sync Extension'}
              </button>
            </div>

            {/* FFmpeg Engine Status */}
            <div style={{ padding: '10px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-tertiary)', border: '1px solid var(--border-default)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>FFmpeg HW Engine</span>
                {toolsStatus?.ffmpeg?.isAvailable ? (
                  <span className="badge badge-success" style={{ fontSize: '8.5px', padding: '1px 4px' }}>ACTIVE</span>
                ) : (
                  <span className="badge badge-danger" style={{ fontSize: '8.5px', padding: '1px 4px' }}>OFFLINE</span>
                )}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {toolsStatus?.ffmpeg?.info || 'Hardware Acceleration Engine'}
              </div>
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
