--[[
================================================================================
   Xdrop — Native Video Importer & Asset Drop Plugin for DaVinci Resolve
   Version 1.2.0 (Unified Design System & Zero-Flicker Architecture)
================================================================================
   Native Fusion UIManager Extension for DaVinci Resolve (Free & Studio).
   Directly docks and interfaces with DaVinci Resolve's Media Pool & Timelines.
   Zero CMD flashes. Zero background popups. Unified modern dark design.
================================================================================
--]]

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

local winID = "XdropResolveWin"
local VERSION = "v1.2.0"

-- Resolve Core Objects
local projectManager = resolve and resolve:GetProjectManager() or (app and app:GetResolve() and app:GetResolve():GetProjectManager())
local project = projectManager and projectManager:GetCurrentProject() or nil
local mediaPool = project and project:GetMediaPool() or nil

local platform = (FuPLATFORM_WINDOWS and "Windows") or
                 (FuPLATFORM_MAC and "Mac") or
                 (FuPLATFORM_LINUX and "Linux")

local Scripts = app and app:MapPath('Scripts:/') or ""

local function script_path()
    return arg and arg[0] or ""
end

local function ScriptIsInstalled()
    local sp = script_path()
    if not sp or sp == "" or not Scripts or Scripts == "" then
        return false
    end
    return sp:find("Scripts") ~= nil
end

local SCRIPT_INSTALLED = ScriptIsInstalled()

-- Default service endpoint
local SERVICE_URL = "http://127.0.0.1:8484"

-- UI Dimensions
local WINDOW_WIDTH = 420
local WINDOW_HEIGHT = 560

-- =============================================================================
-- UNIFIED DESIGN SYSTEM (Zinc / Void / Electric Cyan)
-- =============================================================================

local LOGO_X_CSS = [[
    QLabel {
        color: #00e5ff;
        font-size: 19px;
        font-weight: 900;
        letter-spacing: -0.5px;
    }
]]

local LOGO_DROP_CSS = [[
    QLabel {
        color: #fafafa;
        font-size: 19px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
]]

local SUBTITLE_CSS = [[
    QLabel {
        color: #71717a;
        font-size: 10px;
        font-weight: 500;
    }
]]

local STATUS_CONNECTED_CSS = [[
    QLabel {
        background-color: rgba(34, 197, 94, 0.12);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 7px;
    }
]]

local STATUS_DISCONNECTED_CSS = [[
    QLabel {
        background-color: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 7px;
    }
]]

local TAB_ACTIVE_CSS = [[
    QPushButton {
        background-color: #18181b;
        color: #fafafa;
        border: 1px solid #27272a;
        border-bottom: 2px solid #00e5ff;
        border-radius: 4px 4px 0 0;
        font-size: 11px;
        font-weight: 700;
        min-height: 28px;
        max-height: 28px;
    }
]]

local TAB_INACTIVE_CSS = [[
    QPushButton {
        background-color: transparent;
        color: #71717a;
        border: 1px solid transparent;
        border-radius: 4px 4px 0 0;
        font-size: 11px;
        font-weight: 500;
        min-height: 28px;
        max-height: 28px;
    }
    QPushButton:hover {
        color: #d4d4d8;
        background-color: #121214;
    }
]]

local SECTION_TITLE_CSS = [[
    QLabel {
        color: #a1a1aa;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-top: 2px;
        margin-bottom: 1px;
    }
]]

local INPUT_LINE_CSS = [[
    QLineEdit {
        background-color: #18181b;
        color: #fafafa;
        border: 1px solid #27272a;
        border-radius: 5px;
        padding: 6px 10px;
        font-size: 12px;
        min-height: 30px;
    }
    QLineEdit:focus {
        border: 1px solid #00e5ff;
        background-color: #1c1c20;
    }
]]

local COMBOBOX_CSS = [[
    QComboBox {
        background-color: #18181b;
        color: #e4e4e7;
        border: 1px solid #27272a;
        border-radius: 5px;
        padding: 4px 8px;
        font-size: 11.5px;
        min-height: 28px;
    }
    QComboBox:hover {
        border: 1px solid #3f3f46;
    }
]]

local PRIMARY_BUTTON_CSS = [[
    QPushButton {
        background-color: #00e5ff;
        color: #09090b;
        border: none;
        border-radius: 6px;
        font-size: 12.5px;
        font-weight: 800;
        letter-spacing: 0.3px;
        min-height: 36px;
        max-height: 36px;
    }
    QPushButton:hover {
        background-color: #38bdf8;
    }
    QPushButton:pressed {
        background-color: #0284c7;
    }
    QPushButton:!enabled {
        background-color: #27272a;
        color: #71717a;
    }
]]

local SECONDARY_BUTTON_CSS = [[
    QPushButton {
        background-color: #18181b;
        color: #d4d4d8;
        border: 1px solid #27272a;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 600;
        min-height: 28px;
        max-height: 28px;
        padding: 0 10px;
    }
    QPushButton:hover {
        background-color: #27272a;
        color: #fafafa;
        border: 1px solid #3f3f46;
    }
    QPushButton:pressed {
        background-color: #09090b;
    }
]]

local STATUS_BOX_CSS = [[
    QLabel {
        background-color: #121214;
        border: 1px solid #27272a;
        border-radius: 5px;
        color: #a1a1aa;
        font-size: 11px;
        padding: 8px 10px;
    }
]]

local DIVIDER_CSS = [[
    QLabel {
        background-color: #27272a;
        max-height: 1px;
        min-height: 1px;
    }
]]

-- =============================================================================
-- ZERO-FLICKER SILENT IPC & FILE HELPERS
-- =============================================================================

local function GetIpcBaseDir()
    if platform == "Windows" then
        local localAppData = os.getenv("LOCALAPPDATA") or ""
        if localAppData == "" then
            local user = os.getenv("USERPROFILE") or "C:\\Users\\Default"
            localAppData = user .. "\\AppData\\Local"
        end
        return localAppData .. "\\Xdrop\\ipc"
    else
        local home = os.getenv("HOME") or ""
        return home .. "/.xdrop/ipc"
    end
end

local IPC_DIR = GetIpcBaseDir()
local PATH_SEP = (platform == "Windows" and "\\" or "/")

local function ReadFileContent(filePath)
    if not filePath then return nil end
    local f = io.open(filePath, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

local function WriteFileContent(filePath, content)
    if not filePath or not content then return false end
    local f = io.open(filePath, "w")
    if not f then return false end
    f:write(content)
    f:close()
    return true
end

local function FileExists(filePath)
    if not filePath or filePath == "" then return false end
    if bmd and bmd.fileexists then
        local ok, exists = pcall(bmd.fileexists, filePath)
        if ok and exists then return true end
    end
    local f = io.open(filePath, "rb")
    if f then
        f:close()
        return true
    end
    return false
end

local function EnsureDir(dirPath)
    if not dirPath or dirPath == "" then return false end
    if bmd and bmd.direxists and bmd.direxists(dirPath) then
        return true
    end
    if bmd and bmd.createdir then
        return bmd.createdir(dirPath)
    end
    if platform == "Windows" then
        os.execute('mkdir "' .. dirPath .. '" 2>nul')
    else
        os.execute('mkdir -p "' .. dirPath .. '" 2>/dev/null')
    end
    return true
end

local function ExtractJsonString(jsonStr, key)
    if not jsonStr then return nil end
    local pattern = '"' .. key .. '"%s*:%s*"([^"]+)"'
    local val = jsonStr:match(pattern)
    return val
end

local function ExtractJsonNumber(jsonStr, key)
    if not jsonStr then return nil end
    local pattern = '"' .. key .. '"%s*:%s*([%d%.]+)'
    local val = jsonStr:match(pattern)
    return val and tonumber(val) or nil
end

local SESSIONS_DIR = IPC_DIR .. PATH_SEP .. "sessions"

local function TouchSessionLease()
    EnsureDir(SESSIONS_DIR)
    local leaseFile = SESSIONS_DIR .. PATH_SEP .. "resolve.lease"
    WriteFileContent(leaseFile, tostring(os.time()))
end

local function ReleaseSessionLease()
    local leaseFile = SESSIONS_DIR .. PATH_SEP .. "resolve.lease"
    if platform == "Windows" then
        os.execute('del /f /q "' .. leaseFile .. '" 2>nul')
    else
        os.execute('rm -f "' .. leaseFile .. '" 2>/dev/null')
    end
end

local function IsEngineOnline()
    -- Check IPC heartbeat file with 0 subprocesses and 0 CMD windows
    local hbFile = IPC_DIR .. PATH_SEP .. "heartbeat.json"
    local hb = ReadFileContent(hbFile)
    if hb and hb ~= "" then
        local ts = ExtractJsonNumber(hb, "timestamp")
        if ts then
            local now = os.time()
            if math.abs(now - ts) <= 6 then
                TouchSessionLease()
                return true
            end
        elseif hb:find('"ok"') ~= nil or hb:find('"healthy"') ~= nil then
            TouchSessionLease()
            return true
        end
    end
    return false
end

local function StartEngineBackground()
    if platform == "Windows" then
        local localAppData = os.getenv("LOCALAPPDATA") or ""
        local userProfile = os.getenv("USERPROFILE") or ""
        local candidatePaths = {
            localAppData .. "\\Xdrop\\start_engine.vbs",
            userProfile .. "\\AppData\\Local\\Xdrop\\start_engine.vbs",
            userProfile .. "\\.xdrop\\start_engine.vbs",
        }
        
        -- Also check relative to script directory
        local sp = script_path()
        if sp and sp ~= "" then
            local sdir = sp:match("(.*[/\\])")
            if sdir then
                table.insert(candidatePaths, sdir .. "..\\..\\..\\start_engine.vbs")
                table.insert(candidatePaths, sdir .. "start_engine.vbs")
            end
        end

        for _, vbs in ipairs(candidatePaths) do
            local exists = false
            if bmd and bmd.fileexists then
                exists = bmd.fileexists(vbs)
            else
                local f = io.open(vbs, "r")
                if f then f:close(); exists = true end
            end

            if exists then
                if bmd and bmd.openurl then
                    bmd.openurl(vbs)
                    return true
                else
                    os.execute('wscript.exe //B "' .. vbs .. '"')
                    return true
                end
            end
        end

        -- Safe Fallback: Write zero-flicker launcher to %TEMP%
        local tempDir = os.getenv("TEMP") or os.getenv("TMP") or "C:\\Windows\\Temp"
        local tempVbs = tempDir .. "\\xdrop_silent_start.vbs"
        local tf = io.open(tempVbs, "w")
        if tf then
            tf:write('Set WshShell = CreateObject("WScript.Shell")\r\n')
            tf:write('WshShell.Run "pythonw.exe -m xdrop.main --background", 0, False\r\n')
            tf:close()
            if bmd and bmd.openurl then
                bmd.openurl(tempVbs)
            else
                os.execute('wscript.exe //B "' .. tempVbs .. '"')
            end
            return true
        end
    else
        local home = os.getenv("HOME") or ""
        local sh = home .. "/.xdrop/run.sh"
        if bmd and bmd.fileexists and bmd.fileexists(sh) then
            os.execute(sh .. ' &')
        else
            os.execute('python3 -m xdrop.main --background &')
        end
        return true
    end
    return false
end

-- Refresh Project & MediaPool handles
local function RefreshResolveHandles()
    projectManager = resolve and resolve:GetProjectManager() or (app and app:GetResolve() and app:GetResolve():GetProjectManager())
    if projectManager then
        project = projectManager:GetCurrentProject()
        if project then
            mediaPool = project:GetMediaPool()
        end
    end
end

-- Get list of subfolders in root folder
local function GetBinList()
    RefreshResolveHandles()
    local list = { "000_Xdrop Assets", "Master" }
    if not mediaPool then return list end
    local root = mediaPool:GetRootFolder()
    if not root then return list end

    local subFolders = root:GetSubFolderList() or {}
    for _, f in ipairs(subFolders) do
        local name = f:GetName()
        if name and name ~= "000_Xdrop Assets" and name ~= "Master" then
            table.insert(list, name)
        end
    end
    return list
end

local function GetOrCreateBin(binName)
    RefreshResolveHandles()
    if not mediaPool then return nil end
    local root = mediaPool:GetRootFolder()
    if not root then return nil end

    local actualName = binName or "000_Xdrop Assets"
    local subFolders = root:GetSubFolderList() or {}
    for _, f in ipairs(subFolders) do
        if f:GetName():lower() == actualName:lower() then
            return f
        end
    end

    return mediaPool:AddSubFolder(root, actualName)
end

-- Create full Xdrop bin hierarchy matching standard asset organization
local function SetupXdropBins()
    RefreshResolveHandles()
    if not mediaPool then
        return false, "No active DaVinci Resolve project open."
    end
    local root = mediaPool:GetRootFolder()
    if not root then
        return false, "Could not access Media Pool root folder."
    end

    local xdropRoot = nil
    local subs = root:GetSubFolderList() or {}
    for _, f in ipairs(subs) do
        local nm = f:GetName()
        if nm == "000_Xdrop Assets" or nm == "Xdrop" then
            xdropRoot = f
            break
        end
    end
    if not xdropRoot then
        xdropRoot = mediaPool:AddSubFolder(root, "000_Xdrop Assets")
    end

    if not xdropRoot then
        return false, "Failed to create root Xdrop Assets bin."
    end

    local subNames = {
        "01_Downloads",
        "02_Video Clips",
        "03_Music & SFX",
        "04_Dialogue & Audio",
        "05_Proxies & Renders"
    }

    local existingSub = {}
    local xsubs = xdropRoot:GetSubFolderList() or {}
    for _, sf in ipairs(xsubs) do
        existingSub[sf:GetName()] = sf
    end

    for _, sname in ipairs(subNames) do
        if not existingSub[sname] then
            mediaPool:AddSubFolder(xdropRoot, sname)
        end
    end

    mediaPool:SetCurrentFolder(xdropRoot)
    return true, "Created complete Xdrop bin structure in Media Pool!"
end

-- Import media files into DaVinci Resolve
local function ImportMediaToResolve(filePath, binName, insertTimeline)
    RefreshResolveHandles()
    if not mediaPool then
        return false, "No active DaVinci Resolve project open."
    end

    if not filePath or filePath == "" then
        return false, "No valid media file path provided."
    end

    filePath = filePath:gsub("\\\\", "\\"):gsub("\\", "/")

    local targetBin = GetOrCreateBin(binName or "000_Xdrop Assets")
    if targetBin then
        mediaPool:SetCurrentFolder(targetBin)
    end

    local imported = mediaPool:ImportMedia({ filePath })
    if not imported or #imported == 0 then
        return false, "ImportMedia returned nil for: " .. filePath
    end

    if insertTimeline and project then
        local timeline = project:GetCurrentTimeline()
        if timeline then
            mediaPool:AppendToTimeline(imported)
        end
    end

    return true, "Successfully imported into bin '" .. (binName or "000_Xdrop Assets") .. "'!"
end

-- Install script to DaVinci Resolve scripts directory
local function InstallScriptSelf()
    local src = script_path()
    if not src or src == "" then return false end

    local targets = {}
    if platform == "Windows" then
        local appData = os.getenv("APPDATA") or ""
        if appData ~= "" then
            table.insert(targets, appData .. "\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Comp\\Xdrop.lua")
        end
    elseif platform == "Mac" then
        local home = os.getenv("HOME") or ""
        if home ~= "" then
            table.insert(targets, home .. "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/Xdrop.lua")
        end
    else
        local home = os.getenv("HOME") or ""
        if home ~= "" then
            table.insert(targets, home .. "/.local/share/DaVinciResolve/Fusion/Scripts/Comp/Xdrop.lua")
        end
    end

    local in_f = io.open(src, "rb")
    if not in_f then return false end
    local content = in_f:read("*a")
    in_f:close()

    local successCount = 0
    for _, tgt in ipairs(targets) do
        local pdir = tgt:match("(.*[/\\])")
        if pdir then
            EnsureDir(pdir)
        end
        local out_f = io.open(tgt, "wb")
        if out_f then
            out_f:write(content)
            out_f:close()
            successCount = successCount + 1
        end
    end

    -- Also copy companion DRB starter bin if present next to the script
    local srcDir = src:match("(.*[/\\])") or ""
    local drbSrc = srcDir .. "Xdrop - Starter Bin.drb"
    local drb_in = io.open(drbSrc, "rb")
    if drb_in then
        local drbContent = drb_in:read("*a")
        drb_in:close()
        for _, tgt in ipairs(targets) do
            local pdir = tgt:match("(.*[/\\])")
            if pdir then
                local drbTgt = pdir .. "Xdrop - Starter Bin.drb"
                local drb_out = io.open(drbTgt, "wb")
                if drb_out then
                    drb_out:write(drbContent)
                    drb_out:close()
                end
            end
        end
    end

    -- Also copy companion UI Logo if present next to the script
    local logoSrc = srcDir .. "XdropLogo.png"
    local logo_in = io.open(logoSrc, "rb")
    if logo_in then
        local logoContent = logo_in:read("*a")
        logo_in:close()
        for _, tgt in ipairs(targets) do
            local pdir = tgt:match("(.*[/\\])")
            if pdir then
                local logoTgt = pdir .. "XdropLogo.png"
                local logo_out = io.open(logoTgt, "wb")
                if logo_out then
                    logo_out:write(logoContent)
                    logo_out:close()
                end
            end
        end
    end

    return successCount > 0
end

-- =============================================================================
-- MAIN UI WINDOW CREATION (Unified 3-Tab Architecture)
-- =============================================================================

local function CreateXdropWindow()
    local scriptSource = debug.getinfo(1, "S").source
    local scriptDir = ""
    if scriptSource and scriptSource:sub(1, 1) == "@" then
        scriptDir = scriptSource:sub(2):match("(.*[/\\])") or ""
    end

    local logoCandidates = {}
    if scriptDir ~= "" then
        table.insert(logoCandidates, scriptDir .. "XdropLogo.png")
        table.insert(logoCandidates, scriptDir .. "XdropLogo-32.png")
    end

    if platform == "Windows" then
        local appData = os.getenv("APPDATA") or ""
        if appData ~= "" then
            table.insert(logoCandidates, appData .. "\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Comp\\XdropLogo.png")
            table.insert(logoCandidates, appData .. "\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Comp\\XdropLogo-32.png")
        end
    elseif platform == "Mac" then
        local home = os.getenv("HOME") or ""
        if home ~= "" then
            table.insert(logoCandidates, home .. "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/XdropLogo.png")
        end
    end

    local resolvedLogo = ""
    for _, cand in ipairs(logoCandidates) do
        if FileExists(cand) then
            resolvedLogo = cand
            break
        end
    end

    local headerItems = {
        Weight = 0,
        Spacing = 6,
    }
    if resolvedLogo ~= "" then
        table.insert(headerItems, ui:Label {
            ID = "AppLogoLabel",
            Pixmap = resolvedLogo,
            FixedSize = { 24, 24 },
            ScaledContents = true,
            Weight = 0,
        })
    end
    table.insert(headerItems, ui:Label { Text = "X", StyleSheet = LOGO_X_CSS, Weight = 0 })
    table.insert(headerItems, ui:Label { Text = "drop", StyleSheet = LOGO_DROP_CSS, Weight = 0 })
    table.insert(headerItems, ui:VGap(0, 1))
    table.insert(headerItems, ui:Label { ID = "proj_badge", Text = "Resolve Studio", StyleSheet = SUBTITLE_CSS, Alignment = { AlignVCenter = true }, Weight = 1 })
    table.insert(headerItems, ui:Label { ID = "engine_status", Text = "● Online", StyleSheet = STATUS_CONNECTED_CSS, Weight = 0 })

    local winConfig = {
        ID = winID,
        WindowTitle = "Xdrop",
        FixedSize = { WINDOW_WIDTH, WINDOW_HEIGHT },
        Margin = 14,
        BackgroundColor = { 9, 9, 11 },

        ui:VGroup {
            Spacing = 8,
            ID = "RootLayout",

            -- 1. UNIFIED BRAND HEADER
            ui:HGroup(headerItems),

            -- 2. TAB NAVIGATION BAR
            ui:HGroup {
                Weight = 0,
                Spacing = 2,
                ui:Button { ID = "tab_import_btn", Text = "📥 Import", StyleSheet = TAB_ACTIVE_CSS, Weight = 1 },
                ui:Button { ID = "tab_queue_btn", Text = "📋 Queue", StyleSheet = TAB_INACTIVE_CSS, Weight = 1 },
                ui:Button { ID = "tab_settings_btn", Text = "⚙ Settings", StyleSheet = TAB_INACTIVE_CSS, Weight = 1 },
            },

            ui:Label { FrameStyle = 4, StyleSheet = DIVIDER_CSS, Weight = 0 },

            -- =================================================================
            -- TAB 1: IMPORT VIEW
            -- =================================================================
            ui:VGroup {
                ID = "TabImportView",
                Spacing = 8,
                Weight = 1,

                -- URL Input Section
                ui:VGroup {
                    Weight = 0,
                    Spacing = 3,
                    ui:HGroup {
                        Weight = 0,
                        ui:Label { Text = "MEDIA URL (YOUTUBE, TIKTOK, IG, X, REDDIT)", StyleSheet = SECTION_TITLE_CSS, Weight = 1 },
                        ui:Button { ID = "paste_btn", Text = "Paste", StyleSheet = SECONDARY_BUTTON_CSS, Weight = 0 },
                    },
                    ui:LineEdit {
                        ID = "url_input",
                        PlaceholderText = "Paste video, audio, or social media link...",
                        StyleSheet = INPUT_LINE_CSS,
                        ClearButtonEnabled = true,
                    },
                },

                -- Format & Quality Selection
                ui:VGroup {
                    Weight = 0,
                    Spacing = 3,
                    ui:Label { Text = "FORMAT / QUALITY PRESET", StyleSheet = SECTION_TITLE_CSS },
                    ui:ComboBox {
                        ID = "quality_select",
                        StyleSheet = COMBOBOX_CSS,
                    },
                },

                -- Destination Bin Selection
                ui:VGroup {
                    Weight = 0,
                    Spacing = 3,
                    ui:Label { Text = "DESTINATION BIN IN MEDIA POOL", StyleSheet = SECTION_TITLE_CSS },
                    ui:HGroup {
                        Spacing = 4,
                        ui:ComboBox {
                            ID = "bin_select",
                            StyleSheet = COMBOBOX_CSS,
                            Weight = 1,
                        },
                        ui:Button {
                            ID = "refresh_bins_btn",
                            Text = "↻",
                            StyleSheet = SECONDARY_BUTTON_CSS,
                            Weight = 0,
                        },
                        ui:Button {
                            ID = "create_bins_btn",
                            Text = "+ Bins",
                            StyleSheet = SECONDARY_BUTTON_CSS,
                            Weight = 0,
                        },
                    },
                },

                -- Timeline insert option
                ui:HGroup {
                    Weight = 0,
                    ui:CheckBox {
                        ID = "timeline_checkbox",
                        Text = "Insert directly onto active timeline playhead",
                        CheckState = "Unchecked",
                        StyleSheet = "QCheckBox { color: #a1a1aa; font-size: 11px; }",
                    },
                },

                -- Primary Action Button
                ui:Button {
                    ID = "download_btn",
                    Text = "⚡ DOWNLOAD & DROP TO RESOLVE",
                    StyleSheet = PRIMARY_BUTTON_CSS,
                    Weight = 0,
                },

                -- Live Status Box
                ui:Label {
                    ID = "status_lbl",
                    Text = "Ready to import. Paste a media URL to begin.",
                    StyleSheet = STATUS_BOX_CSS,
                    Weight = 1,
                    Alignment = { AlignTop = true, AlignLeft = true },
                    WordWrap = true,
                },
            },

            -- =================================================================
            -- TAB 2: QUEUE VIEW
            -- =================================================================
            ui:VGroup {
                ID = "TabQueueView",
                Spacing = 8,
                Weight = 1,
                Hidden = true,

                ui:HGroup {
                    Weight = 0,
                    ui:Label { Text = "ACTIVE & RECENT DOWNLOADS", StyleSheet = SECTION_TITLE_CSS, Weight = 1 },
                    ui:Button { ID = "refresh_queue_btn", Text = "↻ Refresh", StyleSheet = SECONDARY_BUTTON_CSS, Weight = 0 },
                },

                ui:Label {
                    ID = "queue_list_lbl",
                    Text = "Checking download queue...",
                    StyleSheet = STATUS_BOX_CSS,
                    Weight = 1,
                    Alignment = { AlignTop = true, AlignLeft = true },
                    WordWrap = true,
                },

                ui:HGroup {
                    Weight = 0,
                    Spacing = 6,
                    ui:Button { ID = "open_downloads_btn", Text = "Open Downloads Folder", StyleSheet = SECONDARY_BUTTON_CSS, Weight = 1 },
                },
            },

            -- =================================================================
            -- TAB 3: SETTINGS VIEW
            -- =================================================================
            ui:VGroup {
                ID = "TabSettingsView",
                Spacing = 8,
                Weight = 1,
                Hidden = true,

                ui:Label { Text = "LOCAL ENGINE SETTINGS", StyleSheet = SECTION_TITLE_CSS, Weight = 0 },

                ui:VGroup {
                    Weight = 0,
                    Spacing = 4,
                    ui:Label { Text = "Service Endpoint: http://127.0.0.1:8484", StyleSheet = "QLabel { color: #fafafa; font-size: 11px; font-weight: 600; }" },
                    ui:Label { Text = "Storage: %LOCALAPPDATA%\\Xdrop\\downloads", StyleSheet = "QLabel { color: #71717a; font-size: 10px; }" },
                },

                ui:Label { FrameStyle = 4, StyleSheet = DIVIDER_CSS, Weight = 0 },

                ui:Label { Text = "RESOLVE INTEGRATION", StyleSheet = SECTION_TITLE_CSS, Weight = 0 },
                ui:HGroup {
                    Weight = 0,
                    Spacing = 6,
                    ui:Button { ID = "setup_bins_full_btn", Text = "Create Xdrop Starter Bins", StyleSheet = SECONDARY_BUTTON_CSS, Weight = 1 },
                    ui:Button { ID = "start_engine_btn", Text = "Restart Engine", StyleSheet = SECONDARY_BUTTON_CSS, Weight = 1 },
                },

                ui:VGap(1, 1),

                ui:Label {
                    ID = "settings_status_lbl",
                    Text = "Xdrop background daemon runs headlessly and handles high-speed extraction silently.",
                    StyleSheet = STATUS_BOX_CSS,
                    Weight = 0,
                    WordWrap = true,
                },
            },
        },
    }

    if resolvedLogo ~= "" then
        winConfig.WindowIcon = resolvedLogo
    end

    local win = disp:AddWindow(winConfig)

    if not win then
        return
    end

    -- =========================================================================
    -- INITIALIZE STATE & COMBOBOXES
    -- =========================================================================

    local qualCombo = win:Find("quality_select")
    qualCombo:Clear()
    qualCombo:AddItem("Best Video (Auto 4K/HD MP4)")
    qualCombo:AddItem("1080p Full HD")
    qualCombo:AddItem("720p HD")
    qualCombo:AddItem("Audio Only (High Quality MP3)")
    qualCombo:AddItem("Audio Only (Lossless WAV)")
    qualCombo.CurrentIndex = 0

    local function PopulateBins()
        local binCombo = win:Find("bin_select")
        binCombo:Clear()
        local bins = GetBinList()
        for _, b in ipairs(bins) do
            binCombo:AddItem(b)
        end
        binCombo.CurrentIndex = 0

        -- Update project context badge
        RefreshResolveHandles()
        local projName = project and project:GetName() or "Resolve Ready"
        win:Find("proj_badge").Text = projName
    end
    PopulateBins()

    local function UpdateEngineStatus(silentAutoStart)
        local statusLabel = win:Find("engine_status")
        local isOnline = IsEngineOnline()
        if isOnline then
            statusLabel.Text = "● Engine Online"
            statusLabel.StyleSheet = STATUS_CONNECTED_CSS
        else
            if silentAutoStart then
                StartEngineBackground()
                if bmd and bmd.wait then bmd.wait(1.5) end
                if IsEngineOnline() then
                    statusLabel.Text = "● Engine Online"
                    statusLabel.StyleSheet = STATUS_CONNECTED_CSS
                    return
                end
            end
            statusLabel.Text = "○ Engine Offline"
            statusLabel.StyleSheet = STATUS_DISCONNECTED_CSS
        end
    end
    UpdateEngineStatus(true)

    -- Tab Switching
    local function SwitchTab(tabName)
        win:Find("TabImportView").Hidden = (tabName ~= "import")
        win:Find("TabQueueView").Hidden = (tabName ~= "queue")
        win:Find("TabSettingsView").Hidden = (tabName ~= "settings")

        win:Find("tab_import_btn").StyleSheet = (tabName == "import") and TAB_ACTIVE_CSS or TAB_INACTIVE_CSS
        win:Find("tab_queue_btn").StyleSheet = (tabName == "queue") and TAB_ACTIVE_CSS or TAB_INACTIVE_CSS
        win:Find("tab_settings_btn").StyleSheet = (tabName == "settings") and TAB_ACTIVE_CSS or TAB_INACTIVE_CSS
    end

    local function RefreshQueueView()
        local qLabel = win:Find("queue_list_lbl")
        local statusDir = IPC_DIR .. PATH_SEP .. "status"
        local jobsDir = IPC_DIR .. PATH_SEP .. "jobs"

        local text = "DOWNLOAD QUEUE / RECENT ACTIVITY:\n\n"
        local hasJobs = false

        -- Check status directory for recent jobs
        if bmd and bmd.fileexists then
            local testJob = statusDir .. PATH_SEP .. "latest.json"
            local latestContent = ReadFileContent(testJob)
            if latestContent and latestContent ~= "" then
                local title = ExtractJsonString(latestContent, "title") or "Media Download"
                local st = ExtractJsonString(latestContent, "status") or "completed"
                local prog = ExtractJsonNumber(latestContent, "progress") or 100
                text = text .. string.format("• %s [%s: %.0f%%]\n", title, st:upper(), prog)
                hasJobs = true
            end
        end

        if not hasJobs then
            text = text .. "No active downloads currently running.\nReady to import new media streams."
        end
        qLabel.Text = text
    end

    -- =========================================================================
    -- EVENT HANDLERS
    -- =========================================================================

    function win.On.tab_import_btn.Clicked(ev)
        SwitchTab("import")
    end

    function win.On.tab_queue_btn.Clicked(ev)
        SwitchTab("queue")
        RefreshQueueView()
    end

    function win.On.tab_settings_btn.Clicked(ev)
        SwitchTab("settings")
    end

    function win.On.refresh_queue_btn.Clicked(ev)
        RefreshQueueView()
    end

    function win.On.refresh_bins_btn.Clicked(ev)
        PopulateBins()
        win:Find("status_lbl").Text = "Refreshed Media Pool bins."
    end

    function win.On.create_bins_btn.Clicked(ev)
        local ok, msg = SetupXdropBins()
        if ok then
            PopulateBins()
            win:Find("status_lbl").Text = msg
        else
            win:Find("status_lbl").Text = "Notice: " .. (msg or "Could not create bins.")
        end
    end

    function win.On.setup_bins_full_btn.Clicked(ev)
        local ok, msg = SetupXdropBins()
        win:Find("settings_status_lbl").Text = ok and "✓ Bins created successfully!" or msg
        PopulateBins()
    end

    function win.On.start_engine_btn.Clicked(ev)
        StartEngineBackground()
        if bmd and bmd.wait then bmd.wait(1.5) end
        UpdateEngineStatus(false)
        win:Find("settings_status_lbl").Text = IsEngineOnline() and "✓ Engine is active on port 8484." or "Engine starting up..."
    end

    function win.On.open_downloads_btn.Clicked(ev)
        local localAppData = os.getenv("LOCALAPPDATA") or ""
        local downDir = localAppData .. "\\Xdrop\\downloads"
        EnsureDir(downDir)
        if bmd and bmd.openurl then
            bmd.openurl(downDir)
        elseif platform == "Windows" then
            os.execute('explorer.exe "' .. downDir .. '"')
        else
            os.execute('open "' .. downDir .. '"')
        end
    end

    function win.On.paste_btn.Clicked(ev)
        -- Clear existing text so user can paste cleanly
        win:Find("url_input"):SetFocus()
        win:Find("status_lbl").Text = "Paste your link using Ctrl+V."
    end

    -- MAIN DOWNLOAD & IMPORT ACTION
    function win.On.download_btn.Clicked(ev)
        local urlInput = win:Find("url_input")
        local rawUrl = urlInput.Text or ""
        rawUrl = rawUrl:match("^%s*(.-)%s*$") -- Trim whitespace

        if rawUrl == "" then
            win:Find("status_lbl").Text = "Please enter or paste a valid media URL."
            return
        end

        local qIndex = win:Find("quality_select").CurrentIndex
        local targetFormat = "video"
        local maxRes = "best"
        local audioOnly = false

        if qIndex == 0 then
            targetFormat = "video"
            maxRes = "best"
        elseif qIndex == 1 then
            targetFormat = "video"
            maxRes = "1080"
        elseif qIndex == 2 then
            targetFormat = "video"
            maxRes = "720"
        elseif qIndex == 3 then
            targetFormat = "audio"
            maxRes = "mp3"
            audioOnly = true
        elseif qIndex == 4 then
            targetFormat = "audio"
            maxRes = "wav"
            audioOnly = true
        end

        local binCombo = win:Find("bin_select")
        local targetBin = binCombo:GetItemText(binCombo.CurrentIndex) or "000_Xdrop Assets"
        local insertTimeline = (win:Find("timeline_checkbox").CheckState == "Checked")

        win:Find("download_btn").Enabled = false
        win:Find("status_lbl").Text = "Preparing download for: " .. rawUrl .. "\nInitializing zero-flicker extraction..."

        -- Ensure IPC directory structure exists silently with ZERO console windows
        local jobsDir = IPC_DIR .. PATH_SEP .. "jobs"
        local statusDir = IPC_DIR .. PATH_SEP .. "status"
        EnsureDir(IPC_DIR)
        EnsureDir(jobsDir)
        EnsureDir(statusDir)

        local jobId = "job_" .. os.time() .. "_" .. math.random(100, 999)
        local payload = string.format([[{"id":"%s","url":"%s","target_format":"%s","max_resolution":"%s","audio_only":%s,"target_editor":"resolve","target_bin":"%s","insert_timeline":%s}]],
            jobId, rawUrl, targetFormat, maxRes, (audioOnly and "true" or "false"), targetBin, (insertTimeline and "true" or "false")
        )

        -- Dispatch silently via IPC file (ZERO subprocesses, ZERO CMD popups)
        local jobFilePath = jobsDir .. PATH_SEP .. jobId .. ".json"
        local wroteIpc = WriteFileContent(jobFilePath, payload)

        win:Find("status_lbl").Text = "Download job queued [" .. jobId .. "]...\nStarting stream download..."

        -- Poll download status SILENTLY via IPC status file (ZERO CMD POPUPS!)
        local completed = false
        local finalJobJson = nil
        local statusFilePath = statusDir .. PATH_SEP .. "job_" .. jobId .. ".json"

        for attempt = 1, 120 do
            if bmd and bmd.wait then bmd.wait(1.0) end

            local jobResp = ReadFileContent(statusFilePath)
            if jobResp and jobResp ~= "" then
                local st = ExtractJsonString(jobResp, "status")
                if st == "downloading" then
                    local pct = ExtractJsonNumber(jobResp, "progress") or 0
                    local spd = ExtractJsonString(jobResp, "speed") or ""
                    win:Find("status_lbl").Text = string.format("Downloading media: %.1f%%%s", pct, (spd ~= "" and (" (" .. spd .. ")") or ""))
                elseif st == "processing" or st == "importing" then
                    win:Find("status_lbl").Text = "Processing media stream & importing into Resolve..."
                elseif st == "completed" then
                    completed = true
                    finalJobJson = jobResp
                    break
                elseif st == "failed" then
                    local err = ExtractJsonString(jobResp, "error_message") or ExtractJsonString(jobResp, "errorMessage") or "Download extractor failed."
                    win:Find("status_lbl").Text = "Download error: " .. err
                    win:Find("download_btn").Enabled = true
                    return
                end
            end
        end

        if completed and finalJobJson then
            local outPath = ExtractJsonString(finalJobJson, "output_file_path") or
                            ExtractJsonString(finalJobJson, "filePath") or
                            ExtractJsonString(finalJobJson, "file_path") or
                            ExtractJsonString(finalJobJson, "outputFilePath")

            if outPath and outPath ~= "" then
                win:Find("status_lbl").Text = "Download complete!\nImporting into Resolve bin: '" .. targetBin .. "'..."
                local ok, impMsg = ImportMediaToResolve(outPath, targetBin, insertTimeline)
                if ok then
                    win:Find("status_lbl").Text = "✓ " .. impMsg
                else
                    win:Find("status_lbl").Text = "Downloaded to: " .. outPath .. "\nResolve notice: " .. tostring(impMsg)
                end
            else
                win:Find("status_lbl").Text = "✓ Download finished! File added to library."
            end
        else
            win:Find("status_lbl").Text = "Download timed out or still running in background. Check your library."
        end

        win:Find("download_btn").Enabled = true
        PopulateBins()
    end

    function win.On.XdropResolveWin.Close(ev)
        ReleaseSessionLease()
        disp:ExitLoop()
    end

    TouchSessionLease()
    win:RecalcLayout()
    win:Show()
    disp:RunLoop()
    ReleaseSessionLease()
    win:Hide()
end

-- =============================================================================
-- ENTRYPOINT
-- =============================================================================

local function Main()
    if not ui or not disp then
        return
    end

    local win = ui:FindWindow(winID)
    if win ~= nil then
        win:RecalcLayout()
        win:Show()
        win:Raise()
        return
    end

    CreateXdropWindow()
end

Main()
collectgarbage("collect")
