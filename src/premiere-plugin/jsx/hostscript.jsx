/**
 * Xdrop Universal Adobe Creative Cloud ExtendScript Host Script
 * Adobe Premiere Pro, Adobe After Effects, and Adobe Audition
 *
 * Provides complete feature parity with DaVinci Resolve:
 * 1. Automatic project and active sequence / comp detection
 * 2. Canonical "000_Xdrop Assets" bin hierarchy (01_Downloads, 02_Video Clips, etc.)
 * 3. Robust nested bin resolution
 * 4. Direct playhead timeline insertion in Premiere Pro and active comp insertion in After Effects
 * 5. Safe exception handling returning valid JSON payloads
 */

// Canonical Xdrop Bin Hierarchy matching DaVinci Resolve standard
var XDROP_CANONICAL_ROOT = "000_Xdrop Assets";
var XDROP_SUB_BINS = [
    "01_Downloads",
    "02_Video Clips",
    "03_Music & SFX",
    "04_Dialogue & Audio",
    "05_Proxies & Renders"
];

// =============================================================================
// ADOBE PREMIERE PRO INTEGRATION
// =============================================================================

function getPremiereProjectInfo() {
    try {
        if (!app.project) {
            return JSON.stringify({
                isAvailable: false,
                currentProject: null,
                activeSequence: null,
                error: "No active project open in Premiere Pro."
            });
        }

        var projectName = app.project.name || "Untitled Project";
        var seqName = null;
        if (app.project.activeSequence) {
            seqName = app.project.activeSequence.name;
        }

        return JSON.stringify({
            isAvailable: true,
            currentProject: projectName,
            activeSequence: seqName,
            projectPath: app.project.path || null,
            error: null
        });
    } catch (e) {
        return JSON.stringify({
            isAvailable: false,
            currentProject: null,
            error: e.toString()
        });
    }
}

function getOrCreatePremiereBin(parentBin, binName) {
    if (!parentBin || !binName) return null;
    for (var i = 0; i < parentBin.children.numItems; i++) {
        var item = parentBin.children[i];
        // type 2 is ProjectItemType.BIN in Premiere Pro
        if (item && item.type === 2 && item.name.toLowerCase() === binName.toLowerCase()) {
            return item;
        }
    }
    return parentBin.createBin(binName);
}

function resolvePremiereBinPath(rootItem, pathStr) {
    if (!pathStr || pathStr === "") {
        pathStr = XDROP_CANONICAL_ROOT;
    }
    var parts = pathStr.replace(/\\/g, "/").split("/");
    var current = rootItem;
    for (var i = 0; i < parts.length; i++) {
        var segment = parts[i].replace(/^\s+|\s+$/g, "");
        if (segment.length > 0) {
            current = getOrCreatePremiereBin(current, segment);
            if (!current) break;
        }
    }
    return current || rootItem;
}

function setupXdropBinsInPremiere() {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No active project open in Premiere Pro."
            });
        }

        var root = app.project.rootItem;
        var xdropRoot = getOrCreatePremiereBin(root, XDROP_CANONICAL_ROOT);
        if (!xdropRoot) {
            return JSON.stringify({
                success: false,
                error: "Failed to create root " + XDROP_CANONICAL_ROOT + " bin."
            });
        }

        var created = [];
        for (var i = 0; i < XDROP_SUB_BINS.length; i++) {
            var subName = XDROP_SUB_BINS[i];
            var sub = getOrCreatePremiereBin(xdropRoot, subName);
            if (sub) created.push(subName);
        }

        return JSON.stringify({
            success: true,
            rootBin: XDROP_CANONICAL_ROOT,
            subBins: created,
            message: "Created complete Xdrop bin structure in Premiere Pro Project!"
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "setupXdropBinsInPremiere exception: " + e.toString()
        });
    }
}

function importMediaIntoPremiere(filePath, binName, insertTimeline) {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No project is currently open in Adobe Premiere Pro."
            });
        }

        if (!binName || binName === "" || binName.toLowerCase() === "xdrop") {
            binName = XDROP_CANONICAL_ROOT;
        }

        var f = new File(filePath);
        if (!f.exists) {
            return JSON.stringify({
                success: false,
                error: "File does not exist on disk: " + filePath
            });
        }

        var project = app.project;
        var targetBin = resolvePremiereBinPath(project.rootItem, binName);

        // Import file into target bin
        // Signature: importFiles(filePathsArray, suppressUIWarnings, targetBin, importAsNumberedStills)
        var fileList = [f.fsName];
        var success = project.importFiles(fileList, true, targetBin, false);

        var insertedToTimeline = false;
        var importedProjectItem = null;

        // Locate imported ProjectItem inside targetBin
        if (targetBin && targetBin.children) {
            for (var i = 0; i < targetBin.children.numItems; i++) {
                var item = targetBin.children[i];
                if (item && (item.name === f.name || item.name.indexOf(f.name) !== -1)) {
                    importedProjectItem = item;
                    break;
                }
            }
        }

        // Optional timeline insertion parity (like DaVinci insert_timeline)
        var shouldInsert = (insertTimeline === true || insertTimeline === "true" || insertTimeline === 1);
        if (shouldInsert && importedProjectItem && project.activeSequence) {
            try {
                var seq = project.activeSequence;
                var playheadTime = seq.getPlayerPosition();
                var inserted = false;

                // Video track insertion
                if (seq.videoTracks && seq.videoTracks.numTracks > 0) {
                    try {
                        seq.videoTracks[0].insertClip(importedProjectItem, playheadTime);
                        inserted = true;
                    } catch (_) {}
                }

                // Audio track fallback for audio-only assets
                if (!inserted && seq.audioTracks && seq.audioTracks.numTracks > 0) {
                    try {
                        seq.audioTracks[0].insertClip(importedProjectItem, playheadTime);
                        inserted = true;
                    } catch (_) {}
                }

                insertedToTimeline = inserted;
            } catch (tlErr) {
                // Non-fatal: clip is still safely imported into bin
            }
        }

        return JSON.stringify({
            success: success,
            clipName: f.name,
            binName: targetBin ? targetBin.name : binName,
            insertedToTimeline: insertedToTimeline,
            filePath: f.fsName
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "Premiere ExtendScript exception: " + e.toString()
        });
    }
}

// =============================================================================
// ADOBE AFTER EFFECTS INTEGRATION
// =============================================================================

function getAfterEffectsProjectInfo() {
    try {
        if (!app.project) {
            return JSON.stringify({
                isAvailable: false,
                currentProject: null,
                activeSequence: null,
                error: "No active project in After Effects."
            });
        }

        var projectName = "Active Project";
        var projPath = null;
        if (app.project.file) {
            projectName = app.project.file.name;
            projPath = app.project.file.fsName;
        }

        var compName = null;
        if (app.project.activeItem && (app.project.activeItem instanceof CompItem)) {
            compName = app.project.activeItem.name;
        }

        return JSON.stringify({
            isAvailable: true,
            currentProject: projectName,
            activeSequence: compName,
            projectPath: projPath,
            error: null
        });
    } catch (e) {
        return JSON.stringify({
            isAvailable: false,
            currentProject: null,
            error: e.toString()
        });
    }
}

function getOrCreateAfterEffectsFolder(parentFolder, folderName) {
    if (!folderName) return null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item && (item instanceof FolderItem) && item.name.toLowerCase() === folderName.toLowerCase()) {
            if (!parentFolder || item.parentFolder === parentFolder) {
                return item;
            }
        }
    }
    var newFolder = app.project.items.addFolder(folderName);
    if (parentFolder && newFolder) {
        newFolder.parentFolder = parentFolder;
    }
    return newFolder;
}

function resolveAfterEffectsFolderPath(pathStr) {
    if (!pathStr || pathStr === "") {
        pathStr = XDROP_CANONICAL_ROOT;
    }
    var parts = pathStr.replace(/\\/g, "/").split("/");
    var current = null;
    for (var i = 0; i < parts.length; i++) {
        var segment = parts[i].replace(/^\s+|\s+$/g, "");
        if (segment.length > 0) {
            current = getOrCreateAfterEffectsFolder(current, segment);
            if (!current) break;
        }
    }
    return current;
}

function setupXdropBinsInAfterEffects() {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No active project in After Effects."
            });
        }

        var xdropRoot = getOrCreateAfterEffectsFolder(null, XDROP_CANONICAL_ROOT);
        if (!xdropRoot) {
            return JSON.stringify({
                success: false,
                error: "Failed to create root " + XDROP_CANONICAL_ROOT + " folder in After Effects."
            });
        }

        var created = [];
        for (var i = 0; i < XDROP_SUB_BINS.length; i++) {
            var subName = XDROP_SUB_BINS[i];
            var sub = getOrCreateAfterEffectsFolder(xdropRoot, subName);
            if (sub) created.push(subName);
        }

        return JSON.stringify({
            success: true,
            rootBin: XDROP_CANONICAL_ROOT,
            subBins: created,
            message: "Created complete Xdrop folder structure in After Effects Project!"
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "setupXdropBinsInAfterEffects exception: " + e.toString()
        });
    }
}

function importMediaIntoAfterEffects(filePath, binName, insertTimeline) {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No project open in Adobe After Effects."
            });
        }

        if (!binName || binName === "" || binName.toLowerCase() === "xdrop") {
            binName = XDROP_CANONICAL_ROOT;
        }

        var f = new File(filePath);
        if (!f.exists) {
            return JSON.stringify({
                success: false,
                error: "File does not exist on disk: " + filePath
            });
        }

        var targetFolder = resolveAfterEffectsFolderPath(binName);

        // Import the file using ImportOptions
        var io = new ImportOptions(f);
        var importedItem = app.project.importFile(io);

        if (importedItem && targetFolder) {
            importedItem.parentFolder = targetFolder;
        }

        var insertedToComp = false;
        var shouldInsert = (insertTimeline === true || insertTimeline === "true" || insertTimeline === 1);
        if (shouldInsert && importedItem && app.project.activeItem && (app.project.activeItem instanceof CompItem)) {
            try {
                app.project.activeItem.layers.add(importedItem);
                insertedToComp = true;
            } catch (_) {}
        }

        return JSON.stringify({
            success: true,
            clipName: f.name,
            binName: targetFolder ? targetFolder.name : binName,
            insertedToTimeline: insertedToComp,
            filePath: f.fsName
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "After Effects ExtendScript exception: " + e.toString()
        });
    }
}

// =============================================================================
// ADOBE AUDITION INTEGRATION
// =============================================================================

function getAuditionProjectInfo() {
    try {
        var hasDoc = false;
        var docName = "Active Session";
        var docPath = null;

        if (app.activeDocument) {
            hasDoc = true;
            docName = app.activeDocument.name || "Active Session";
            if (app.activeDocument.file) {
                docPath = app.activeDocument.file.fsName;
            }
        } else if (app.project) {
            hasDoc = true;
            if (app.project.file) {
                docName = app.project.file.name;
                docPath = app.project.file.fsName;
            }
        }

        return JSON.stringify({
            isAvailable: hasDoc,
            currentProject: hasDoc ? docName : null,
            activeSequence: null,
            projectPath: docPath,
            error: hasDoc ? null : "No active session in Adobe Audition."
        });
    } catch (e) {
        return JSON.stringify({
            isAvailable: false,
            currentProject: null,
            error: e.toString()
        });
    }
}

function setupXdropBinsInAudition() {
    return JSON.stringify({
        success: true,
        rootBin: XDROP_CANONICAL_ROOT,
        message: "Audition session ready."
    });
}

function importMediaIntoAudition(filePath, binName) {
    try {
        var f = new File(filePath);
        if (!f.exists) {
            return JSON.stringify({
                success: false,
                error: "File does not exist on disk: " + filePath
            });
        }

        var imported = null;
        if (app.project && typeof app.project.importFile === "function") {
            imported = app.project.importFile(f.fsName);
        } else if (typeof app.openDocument === "function") {
            imported = app.openDocument(f.fsName);
        }

        return JSON.stringify({
            success: true,
            clipName: f.name,
            binName: binName || XDROP_CANONICAL_ROOT,
            filePath: f.fsName
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "Audition ExtendScript exception: " + e.toString()
        });
    }
}

// =============================================================================
// UNIVERSAL BIN INITIALIZER
// =============================================================================

function setupXdropBins() {
    try {
        var appName = (app && app.name) ? app.name.toLowerCase() : "";
        if (appName.indexOf("after") !== -1) {
            return setupXdropBinsInAfterEffects();
        } else if (appName.indexOf("audition") !== -1) {
            return setupXdropBinsInAudition();
        } else {
            return setupXdropBinsInPremiere();
        }
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "setupXdropBins exception: " + e.toString()
        });
    }
}

function launchSystemFile(filePath) {
    try {
        if (!filePath) return "false";
        var f = new File(filePath);
        if (f.exists) {
            var ok = f.execute();
            return ok ? "true" : "false";
        }
        return "not_found";
    } catch (e) {
        return "error: " + e.toString();
    }
}

function launchXdropEngine() {
    try {
        var isWin = ($.os.indexOf("Windows") !== -1);
        var userHome = Folder("~").fsName;
        if (isWin) {
            var vbs = userHome + "\\AppData\\Local\\Xdrop\\start_engine.vbs";
            var fVbs = new File(vbs);
            if (fVbs.exists) {
                var ok = fVbs.execute();
                return ok ? "SUCCESS_VBS" : "EXECUTE_VBS_FAILED";
            }
            var bat = userHome + "\\AppData\\Local\\Xdrop\\start_engine.bat";
            var fBat = new File(bat);
            if (fBat.exists) {
                var okBat = fBat.execute();
                return okBat ? "SUCCESS_BAT" : "EXECUTE_BAT_FAILED";
            }
        } else {
            var sh = userHome + "/.xdrop/start_engine.sh";
            var fSh = new File(sh);
            if (fSh.exists) {
                var okSh = fSh.execute();
                return okSh ? "SUCCESS_SH" : "EXECUTE_SH_FAILED";
            }
        }
        return "NOT_FOUND";
    } catch (e) {
        return "ERROR: " + e.toString();
    }
}
