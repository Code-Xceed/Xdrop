import React, { useState, useEffect } from 'react';
import { DownloadJob } from '@xdrop/shared-types';
import { wsService } from './services/ws';
import { listDownloads } from './services/api';
import { EditorProvider } from './context/EditorContext';
import { ThemeProvider } from './context/ThemeContext';
import { Header } from './components/Header';
import { Navigation, TabId } from './components/Navigation';
import { ImportPage } from './pages/ImportPage';
import { QueuePage } from './pages/QueuePage';
import { LibraryPage } from './pages/LibraryPage';
import { SettingsPage } from './pages/SettingsPage';
import { ToastContainer, ToastMessage } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabId>('import');
  // Maintain all opened panels in memory so state, inputs, scroll & data are never lost
  const [visitedTabs, setVisitedTabs] = useState<Set<TabId>>(() => new Set<TabId>(['import']));
  const [downloads, setDownloads] = useState<DownloadJob[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const handleSelectTab = (tab: TabId) => {
    setVisitedTabs((prev) => {
      if (prev.has(tab)) return prev;
      const next = new Set(prev);
      next.add(tab);
      return next;
    });
    setCurrentTab(tab);
  };

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const refreshDownloads = async () => {
    try {
      const list = await listDownloads();
      setDownloads(list);
    } catch (_) {}
  };

  useEffect(() => {
    // Initial fetch
    refreshDownloads();

    // Connect WebSocket
    wsService.connect();

    const unsubscribe = wsService.subscribe((msg: any) => {
      const type = msg.type;
      const payload = msg.payload;

      if (type === 'INITIAL_STATE') {
        if (payload?.downloads) setDownloads(payload.downloads);
      } else if (type === 'JOB_CREATED') {
        if (payload?.job) {
          setDownloads((prev) => [payload.job, ...prev.filter((j) => j.id !== payload.job.id)]);
        }
      } else if (type === 'JOB_PROGRESS' || type === 'JOB_UPDATED') {
        const prog = payload?.progress;
        if (prog) {
          setDownloads((prev) =>
            prev.map((j) =>
              j.id === prog.id
                ? {
                    ...j,
                    status: prog.status,
                    progress: prog.progress,
                    downloadedBytes: prog.downloadedBytes,
                    totalBytes: prog.totalBytes ?? j.totalBytes,
                    speed: prog.speed,
                    eta: prog.eta,
                    errorMessage: prog.errorMessage ?? j.errorMessage,
                    resolveImported: prog.resolveImported ?? j.resolveImported,
                    premiereImported: prog.premiereImported ?? j.premiereImported,
                    aftereffectsImported: prog.aftereffectsImported ?? j.aftereffectsImported,
                  }
                : j
            )
          );
        }
      } else if (type === 'JOB_COMPLETED') {
        const compJob = payload?.job;
        if (compJob) {
          setDownloads((prev) =>
            prev.map((j) => (j.id === compJob.id ? compJob : j))
          );
          showToast(`Completed: ${compJob.title}`, 'success');
        }
      } else if (type === 'JOB_FAILED') {
        const jobId = payload?.jobId;
        const errMsg = payload?.message || 'Download failed.';
        setDownloads((prev) =>
          prev.map((j) =>
            j.id === jobId ? { ...j, status: 'failed', errorMessage: errMsg } : j
          )
        );
        showToast(errMsg, 'error');
      } else if (type === 'JOB_REMOVED') {
        const jobId = payload?.jobId;
        if (jobId) {
          setDownloads((prev) => prev.filter((j) => j.id !== jobId));
        }
      }
    });

    // Keyboard shortcuts: 1, 2, 3, 4
    const handleGlobalKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === '1') handleSelectTab('import');
      if (e.key === '2') handleSelectTab('queue');
      if (e.key === '3') handleSelectTab('library');
      if (e.key === '4') handleSelectTab('settings');
    };
    window.addEventListener('keydown', handleGlobalKey);

    return () => {
      unsubscribe();
      window.removeEventListener('keydown', handleGlobalKey);
    };
  }, []);

  // Ensure any programmatic tab changes are tracked in visitedTabs
  useEffect(() => {
    setVisitedTabs((prev) => {
      if (prev.has(currentTab)) return prev;
      const next = new Set(prev);
      next.add(currentTab);
      return next;
    });
  }, [currentTab]);

  const activeQueueCount = downloads.filter(
    (j) => j.status === 'downloading' || j.status === 'processing' || j.status === 'importing' || j.status === 'queued'
  ).length;

  return (
    <EditorProvider>
      <ThemeProvider>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-void)' }}>
          <Header />

          <Navigation
            currentTab={currentTab}
            onSelectTab={handleSelectTab}
            activeQueueCount={activeQueueCount}
          />

          <ErrorBoundary>
            <main
              style={{
                flex: 1,
                position: 'relative',
                overflow: 'hidden',
                minHeight: 0,
                width: '100%',
              }}
            >
              {/* 1. Import Panel: Preserves URL, analyzed metadata, thumbnails, custom selections */}
              {visitedTabs.has('import') && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    visibility: currentTab === 'import' ? 'visible' : 'hidden',
                    pointerEvents: currentTab === 'import' ? 'auto' : 'none',
                    zIndex: currentTab === 'import' ? 1 : 0,
                  }}
                >
                  <ImportPage
                    onJobStarted={() => {
                      handleSelectTab('queue');
                      refreshDownloads();
                    }}
                    showToast={showToast}
                  />
                </div>
              )}

              {/* 2. Queue Panel: Preserves filter tabs, scroll, per-job target editor choices */}
              {visitedTabs.has('queue') && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    visibility: currentTab === 'queue' ? 'visible' : 'hidden',
                    pointerEvents: currentTab === 'queue' ? 'auto' : 'none',
                    zIndex: currentTab === 'queue' ? 1 : 0,
                  }}
                >
                  <QueuePage
                    downloads={downloads}
                    onRefresh={refreshDownloads}
                    showToast={showToast}
                  />
                </div>
              )}

              {/* 3. Library Panel: Preserves search query, platform filters, editor targets */}
              {visitedTabs.has('library') && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    visibility: currentTab === 'library' ? 'visible' : 'hidden',
                    pointerEvents: currentTab === 'library' ? 'auto' : 'none',
                    zIndex: currentTab === 'library' ? 1 : 0,
                  }}
                >
                  <LibraryPage
                    showToast={showToast}
                    isActive={currentTab === 'library'}
                  />
                </div>
              )}

              {/* 4. Settings Panel: Preserves edited inputs and configurations */}
              {visitedTabs.has('settings') && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    visibility: currentTab === 'settings' ? 'visible' : 'hidden',
                    pointerEvents: currentTab === 'settings' ? 'auto' : 'none',
                    zIndex: currentTab === 'settings' ? 1 : 0,
                  }}
                >
                  <SettingsPage showToast={showToast} />
                </div>
              )}
            </main>
          </ErrorBoundary>

          <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </div>
      </ThemeProvider>
    </EditorProvider>
  );
};
