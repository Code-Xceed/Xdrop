/**
 * DaVinci Resolve Studio Workflow Integration Main Process.
 * Managed by DaVinci Resolve Studio when opened from Workspace -> Workflow Integrations.
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');
const { exec, spawn } = require('child_process');

function checkEngineOnline(port = 8484) {
    return new Promise((resolve) => {
        const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
            resolve(res.statusCode === 200);
        });
        req.on('error', () => resolve(false));
        req.setTimeout(800, () => {
            try { req.abort(); } catch (_) {}
            resolve(false);
        });
    });
}

let _backendStartingPromise = null;

async function startBackendHeadless() {
    if (await checkEngineOnline(8484)) {
        return true;
    }
    if (_backendStartingPromise) {
        return _backendStartingPromise;
    }

    _backendStartingPromise = (async () => {
        const localAppData = process.env.LOCALAPPDATA || (process.env.USERPROFILE ? path.join(process.env.USERPROFILE, 'AppData', 'Local') : '');
        const xdropDir = path.join(localAppData, 'Xdrop');
        const runEngineScript = path.join(xdropDir, 'run_engine.py');
        const vbsPath = path.join(xdropDir, 'start_engine.vbs');

        // Locate pythonw executable
        let pythonwExe = 'pythonw.exe';
        const candidates = [
            'C:\\Program Files\\Python314\\pythonw.exe',
            'C:\\Program Files\\Python313\\pythonw.exe',
            'C:\\Program Files\\Python312\\pythonw.exe',
            'C:\\Program Files\\Python311\\pythonw.exe',
            'C:\\Program Files\\Python310\\pythonw.exe',
            path.join(localAppData, 'Programs', 'Python', 'Python314', 'pythonw.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python313', 'pythonw.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python312', 'pythonw.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python311', 'pythonw.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python310', 'pythonw.exe'),
            'C:\\Python314\\pythonw.exe',
            'C:\\Python313\\pythonw.exe',
            'C:\\Python312\\pythonw.exe',
            'C:\\Python311\\pythonw.exe',
            'C:\\Python310\\pythonw.exe',
        ];
        for (const c of candidates) {
            if (c && fs.existsSync(c)) {
                pythonwExe = c;
                break;
            }
        }

        try {
            if (fs.existsSync(runEngineScript) && fs.existsSync(pythonwExe)) {
                const child = spawn(pythonwExe, [runEngineScript, '--background'], {
                    detached: true,
                    stdio: 'ignore',
                    windowsHide: true,
                    cwd: xdropDir
                });
                child.unref();
            } else if (fs.existsSync(vbsPath)) {
                const child = spawn('wscript.exe', ['//B', vbsPath], {
                    detached: true,
                    stdio: 'ignore',
                    windowsHide: true,
                    cwd: xdropDir
                });
                child.unref();
            } else {
                const child = spawn(pythonwExe, ['-m', 'xdrop.main', '--background'], {
                    detached: true,
                    stdio: 'ignore',
                    windowsHide: true,
                    cwd: xdropDir
                });
                child.unref();
            }
        } catch (err) {
            console.warn('[Xdrop Studio] Could not trigger backend startup:', err);
        }

        for (let i = 0; i < 15; i++) {
            await new Promise((r) => setTimeout(r, 400));
            if (await checkEngineOnline(8484)) {
                return true;
            }
        }
        return false;
    })().finally(() => {
        _backendStartingPromise = null;
    });

    return _backendStartingPromise;
}

const PLUGIN_ID = 'com.xdrop.resolve.workflowintegration';

let WorkflowIntegration = null;
try {
    WorkflowIntegration = require('./WorkflowIntegration.node');
} catch (e) {
    console.warn('[Xdrop Studio] WorkflowIntegration native binary not available in this context:', e);
}

let resolveObj = null;
let projectManagerObj = null;
let mainWindow = null;

async function initResolveInterface() {
    if (!WorkflowIntegration) return null;
    try {
        const isSuccess = await WorkflowIntegration.Initialize(PLUGIN_ID);
        if (!isSuccess) {
            console.error('[Xdrop Studio] Failed to initialize Resolve interface');
            return null;
        }
        resolveObj = await WorkflowIntegration.GetResolve();
        return resolveObj;
    } catch (e) {
        console.error('[Xdrop Studio] Error initializing Resolve:', e);
        return null;
    }
}

async function getResolve() {
    if (!resolveObj) {
        resolveObj = await initResolveInterface();
    }
    return resolveObj;
}

async function getCurrentProject() {
    const resolve = await getResolve();
    if (!resolve) return null;
    projectManagerObj = resolve.GetProjectManager();
    if (!projectManagerObj) return null;
    return projectManagerObj.GetCurrentProject();
}

function registerResolveEventHandlers() {
    ipcMain.handle('resolve:getProjectInfo', async () => {
        try {
            const project = await getCurrentProject();
            if (!project) return { isAvailable: false, error: 'No active project' };
            const name = project.GetName();
            const mediaPool = project.GetMediaPool();
            const rootFolder = mediaPool ? mediaPool.GetRootFolder() : null;
            return {
                isAvailable: true,
                currentProject: name,
                rootFolder: rootFolder ? rootFolder.GetName() : 'Master'
            };
        } catch (e) {
            return { isAvailable: false, error: String(e) };
        }
    });

    ipcMain.handle('resolve:createBin', async (event, binName) => {
        try {
            const project = await getCurrentProject();
            if (!project) return false;
            const mediaPool = project.GetMediaPool();
            const rootFolder = mediaPool.GetRootFolder();
            const newFolder = mediaPool.AddSubFolder(rootFolder, binName);
            return Boolean(newFolder);
        } catch (e) {
            console.error('[Xdrop Studio] createBin error:', e);
            return false;
        }
    });

    ipcMain.handle('resolve:selectBin', async (event, binName) => {
        try {
            const project = await getCurrentProject();
            if (!project) return false;
            const mediaPool = project.GetMediaPool();
            const rootFolder = mediaPool.GetRootFolder();
            const subFolders = rootFolder.GetSubFolderList() || [];
            const found = subFolders.find(f => f.GetName().toLowerCase() === String(binName).toLowerCase());
            if (found) {
                return mediaPool.SetCurrentFolder(found);
            }
            return false;
        } catch (e) {
            return false;
        }
    });

    ipcMain.handle('resolve:addClips', async (event, filePathsArray) => {
        try {
            const project = await getCurrentProject();
            if (!project) return { success: false, error: 'No active project' };
            const mediaPool = project.GetMediaPool();
            const paths = Array.isArray(filePathsArray) ? filePathsArray : [filePathsArray];
            const clips = mediaPool.ImportMedia(paths);
            return {
                success: Array.isArray(clips) && clips.length > 0,
                clipsCount: clips ? clips.length : 0
            };
        } catch (e) {
            return { success: false, error: String(e) };
        }
    });

    ipcMain.handle('resolve:startBackend', async () => {
        return await startBackendHeadless();
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 440,
        height: 720,
        minWidth: 360,
        minHeight: 520,
        title: 'Xdrop',
        backgroundColor: '#09090b',
        autoHideMenuBar: true,
        useContentSize: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
    });

    mainWindow.setMenuBarVisibility(false);
    if (mainWindow.removeMenu) {
        mainWindow.removeMenu();
    }
    mainWindow.loadFile(path.join(__dirname, 'index.html'));
}

if (app) {
    app.whenReady().then(async () => {
        registerResolveEventHandlers();
        // Automatically start the background Python engine headless
        startBackendHeadless().catch((err) => {
            console.warn('[Xdrop Studio] Background engine auto-start notice:', err);
        });
        await initResolveInterface();
        createWindow();
    });

    app.on('window-all-closed', () => {
        if (WorkflowIntegration) {
            try {
                WorkflowIntegration.CleanUp();
            } catch (_) {}
        }
        if (process.platform !== 'darwin') {
            app.quit();
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
}
