import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  EditorsStatus,
  ResolveStatus,
  PremiereStatus,
  AfterEffectsStatus,
  SupportedEditor
} from '@xdrop/shared-types';
import { getEditorsStatus } from '../services/api';

export interface EditorContextValue {
  activeEditor: SupportedEditor;
  detectedHost: 'resolve' | 'premiere' | 'aftereffects' | 'standalone';
  editorsStatus: EditorsStatus | null;
  resolveStatus: ResolveStatus | null;
  premiereStatus: PremiereStatus | null;
  aftereffectsStatus: AfterEffectsStatus | null;
  activeEditorName: string;
  activeProjectName: string | null;
  activeSequenceOrTimeline: string | null;
  isEditorConnected: boolean;
  setActiveEditor: (editor: SupportedEditor) => void;
  refreshEditorsStatus: (silent?: boolean) => Promise<void>;
  isRefreshing: boolean;
}

const EditorContext = createContext<EditorContextValue | undefined>(undefined);

export const EditorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 1. Detect Host from URL Query or Environment
  const [detectedHost, setDetectedHost] = useState<'resolve' | 'premiere' | 'aftereffects' | 'standalone'>(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const h = params.get('host');
      if (h === 'aftereffects') return 'aftereffects';
      if (h === 'premiere') return 'premiere';
      if (h === 'resolve') return 'resolve';
    } catch (_) {}
    return 'standalone';
  });

  const [activeEditor, setActiveEditorState] = useState<SupportedEditor>(() => {
    const saved = (localStorage.getItem('xdrop_active_editor') || localStorage.getItem('resolvefetch_active_editor')) as SupportedEditor;
    if (saved && (saved === 'resolve' || saved === 'premiere' || saved === 'aftereffects')) {
      return saved;
    }
    return detectedHost === 'aftereffects'
      ? 'aftereffects'
      : detectedHost === 'premiere'
      ? 'premiere'
      : detectedHost === 'resolve'
      ? 'resolve'
      : 'resolve';
  });

  const [editorsStatus, setEditorsStatus] = useState<EditorsStatus | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const setActiveEditor = (ed: SupportedEditor) => {
    setActiveEditorState(ed);
    try {
      localStorage.setItem('xdrop_active_editor', ed);
    } catch (_) {}
  };

  const refreshEditorsStatus = useCallback(async (silent = false) => {
    if (!silent) setIsRefreshing(true);
    try {
      const status = await getEditorsStatus();
      setEditorsStatus(status);

      // Auto-set active editor if currently none or matching detected host
      if (detectedHost === 'aftereffects') {
        setActiveEditorState('aftereffects');
      } else if (detectedHost === 'premiere') {
        setActiveEditorState('premiere');
      } else if (detectedHost === 'resolve') {
        setActiveEditorState('resolve');
      } else {
        const saved = (localStorage.getItem('xdrop_active_editor') || localStorage.getItem('resolvefetch_active_editor')) as SupportedEditor;
        if (!saved && status.activeEditor && status.activeEditor !== 'none') {
          setActiveEditorState(status.activeEditor);
        }
      }
    } catch (e) {
      console.warn('[EditorContext] Editors status check note:', e);
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  }, [detectedHost]);

  // Listen for CEP parent postMessage
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === 'HOST_INFO') {
        if (event.data.host === 'aftereffects') {
          setDetectedHost('aftereffects');
          setActiveEditorState('aftereffects');
          if (event.data.projectInfo) {
            setEditorsStatus((prev) => ({
              activeEditor: 'aftereffects',
              resolve: prev?.resolve || { isAvailable: false, lastChecked: new Date().toISOString() },
              premiere: prev?.premiere || { isAvailable: false, lastChecked: new Date().toISOString() },
              aftereffects: {
                isAvailable: event.data.projectInfo.isAvailable ?? true,
                productName: 'Adobe After Effects',
                currentProject: event.data.projectInfo.currentProject,
                activeSequence: event.data.projectInfo.activeSequence,
                projectPath: event.data.projectInfo.projectPath,
                error: event.data.projectInfo.error,
                lastChecked: new Date().toISOString()
              }
            }));
          }
        } else if (event.data.host === 'premiere') {
          setDetectedHost('premiere');
          setActiveEditorState('premiere');
          if (event.data.projectInfo) {
            setEditorsStatus((prev) => ({
              activeEditor: 'premiere',
              resolve: prev?.resolve || { isAvailable: false, lastChecked: new Date().toISOString() },
              premiere: {
                isAvailable: event.data.projectInfo.isAvailable ?? true,
                productName: 'Adobe Premiere Pro',
                currentProject: event.data.projectInfo.currentProject,
                activeSequence: event.data.projectInfo.activeSequence,
                projectPath: event.data.projectInfo.projectPath,
                error: event.data.projectInfo.error,
                lastChecked: new Date().toISOString()
              },
              aftereffects: prev?.aftereffects || { isAvailable: false, lastChecked: new Date().toISOString() }
            }));
          }
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Ask parent frame if inside CEP iframe
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'REQUEST_HOST_INFO' }, '*');
      }
    } catch (_) {}

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  // Periodic silent polling every 10 seconds
  useEffect(() => {
    refreshEditorsStatus(true);
    const interval = setInterval(() => {
      refreshEditorsStatus(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [refreshEditorsStatus]);

  const resolveStatus = editorsStatus?.resolve || null;
  const premiereStatus = editorsStatus?.premiere || null;
  const aftereffectsStatus = editorsStatus?.aftereffects || null;

  let activeEditorName = 'Video Editor';
  let activeProjectName: string | null = null;
  let activeSequenceOrTimeline: string | null = null;
  let isEditorConnected = false;

  if (activeEditor === 'aftereffects') {
    activeEditorName = 'Adobe After Effects';
    isEditorConnected = aftereffectsStatus?.isAvailable ?? false;
    activeProjectName = aftereffectsStatus?.currentProject || null;
    activeSequenceOrTimeline = aftereffectsStatus?.activeSequence || null;
  } else if (activeEditor === 'premiere') {
    activeEditorName = 'Adobe Premiere Pro';
    isEditorConnected = premiereStatus?.isAvailable ?? false;
    activeProjectName = premiereStatus?.currentProject || null;
    activeSequenceOrTimeline = premiereStatus?.activeSequence || null;
  } else if (activeEditor === 'resolve') {
    activeEditorName = 'DaVinci Resolve';
    isEditorConnected = resolveStatus?.isAvailable ?? false;
    activeProjectName = resolveStatus?.currentProject || null;
    activeSequenceOrTimeline = resolveStatus?.currentTimeline || null;
  }

  return (
    <EditorContext.Provider
      value={{
        activeEditor,
        detectedHost,
        editorsStatus,
        resolveStatus,
        premiereStatus,
        aftereffectsStatus,
        activeEditorName,
        activeProjectName,
        activeSequenceOrTimeline,
        isEditorConnected,
        setActiveEditor,
        refreshEditorsStatus,
        isRefreshing,
      }}
    >
      {children}
    </EditorContext.Provider>
  );
};

export const useEditorContext = () => {
  const context = useContext(EditorContext);
  if (!context) {
    throw new Error('useEditorContext must be used within an EditorProvider');
  }
  return context;
};
