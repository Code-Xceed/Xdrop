/**
 * Xdrop Adobe Premiere Pro & After Effects ExtendScript Host Script
 * Handles project detection, bin creation, and file importing
 */

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

        var projectName = app.project.name;
        var seqName = null;
        if (app.project.activeSequence) {
            seqName = app.project.activeSequence.name;
        }

        return JSON.stringify({
            isAvailable: true,
            currentProject: projectName,
            activeSequence: seqName,
            projectPath: app.project.path,
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

function importMediaIntoPremiere(filePath, binName) {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No project is currently open in Adobe Premiere Pro."
            });
        }

        if (!binName || binName === "") {
            binName = "Xdrop";
        }

        var project = app.project;
        var targetBin = null;

        // Search root project items for existing bin
        for (var i = 0; i < project.rootItem.children.numItems; i++) {
            var item = project.rootItem.children[i];
            // type 2 is ProjectItemType.BIN in Premiere Pro
            if (item.type === 2 && item.name.toLowerCase() === binName.toLowerCase()) {
                targetBin = item;
                break;
            }
        }

        // Create bin if it doesn't exist yet
        if (!targetBin) {
            targetBin = project.rootItem.createBin(binName);
        }

        // Verify file exists
        var f = new File(filePath);
        if (!f.exists) {
            return JSON.stringify({
                success: false,
                error: "File does not exist on disk: " + filePath
            });
        }

        // Import file into target bin
        // Signature: importFiles(filePathsArray, suppressUIWarnings, targetBin, importAsNumberedStills)
        var fileList = [f.fsName];
        var success = project.importFiles(fileList, true, targetBin, false);

        return JSON.stringify({
            success: success,
            clipName: f.name,
            binName: targetBin.name,
            filePath: f.fsName
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "ExtendScript exception: " + e.toString()
        });
    }
}

/**
 * Xdrop Adobe After Effects ExtendScript Integration
 */
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

function importMediaIntoAfterEffects(filePath, binName) {
    try {
        if (!app.project) {
            return JSON.stringify({
                success: false,
                error: "No project open in Adobe After Effects."
            });
        }

        if (!binName || binName === "") {
            binName = "Xdrop";
        }

        var f = new File(filePath);
        if (!f.exists) {
            return JSON.stringify({
                success: false,
                error: "File does not exist on disk: " + filePath
            });
        }

        // Find or create target folder in After Effects Project panel
        var targetFolder = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item && (item instanceof FolderItem) && item.name.toLowerCase() === binName.toLowerCase()) {
                targetFolder = item;
                break;
            }
        }

        if (!targetFolder) {
            targetFolder = app.project.items.addFolder(binName);
        }

        // Import the file using ImportOptions
        var io = new ImportOptions(f);
        var importedItem = app.project.importFile(io);

        if (importedItem && targetFolder) {
            importedItem.parentFolder = targetFolder;
        }

        return JSON.stringify({
            success: true,
            clipName: f.name,
            binName: targetFolder ? targetFolder.name : binName,
            filePath: f.fsName
        });
    } catch (e) {
        return JSON.stringify({
            success: false,
            error: "After Effects ExtendScript exception: " + e.toString()
        });
    }
}
