// Preload script for DaVinci Resolve Studio Workflow Integration
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('resolveAPI', {
    // Media import
    addClips: (filePathsArray) => ipcRenderer.invoke('resolve:addClips', filePathsArray),
    createBin: (binName) => ipcRenderer.invoke('resolve:createBin', binName),
    selectBin: (binName) => ipcRenderer.invoke('resolve:selectBin', binName),

    // Project & Timeline info
    getProjectInfo: () => ipcRenderer.invoke('resolve:getProjectInfo'),

    // Background service control
    startBackend: () => ipcRenderer.invoke('resolve:startBackend'),

    // Environment info
    isStudioEnvironment: () => true,
});
