--[[
================================================================================
   Xdrop — Cross-NLE Universal Media & Social Asset Importer
   DaVinci Resolve Native Extension (Unified Studio Architecture)
================================================================================
   Launches the unified modern React Studio UI as a dedicated standalone
   desktop window seamlessly integrated with DaVinci Resolve.
   Zero CMD flashes. Zero background popups. Unified modern design.
================================================================================
--]]

local winID = "XdropResolveWin"
local VERSION = "v1.2.0"
local SERVICE_URL = "http://127.0.0.1:8484?host=resolve"

-- DaVinci Resolve Core Handles
local projectManager = resolve and resolve:GetProjectManager() or (app and app:GetResolve() and app:GetResolve():GetProjectManager())
local project = projectManager and projectManager:GetCurrentProject() or nil
local mediaPool = project and project:GetMediaPool() or nil

local platform = (FuPLATFORM_WINDOWS and "Windows") or
                 (FuPLATFORM_MAC and "Mac") or
                 (FuPLATFORM_LINUX and "Linux") or "Windows"

-- =============================================================================
-- FILE & DIRECTORY HELPERS
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

local function ExtractJsonNumber(jsonStr, key)
    if not jsonStr then return nil end
    local pattern = '"' .. key .. '"%s*:%s*([%d%.]+)'
    local val = jsonStr:match(pattern)
    return val and tonumber(val) or nil
end

-- =============================================================================
-- SESSION LEASE MANAGEMENT
-- =============================================================================

local SESSIONS_DIR = IPC_DIR .. PATH_SEP .. "sessions"

local function TouchSessionLease()
    EnsureDir(SESSIONS_DIR)
    local leaseFile = SESSIONS_DIR .. PATH_SEP .. "resolve.lease"
    WriteFileContent(leaseFile, tostring(os.time()))
end

-- =============================================================================
-- DAVINCI RESOLVE BIN PREPARATION
-- =============================================================================

local function SetupXdropBins()
    projectManager = resolve and resolve:GetProjectManager() or (app and app:GetResolve() and app:GetResolve():GetProjectManager())
    if projectManager then
        project = projectManager:GetCurrentProject()
        if project then
            mediaPool = project:GetMediaPool()
        end
    end

    if not mediaPool then
        return false
    end

    local root = mediaPool:GetRootFolder()
    if not root then return false end

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

    if xdropRoot then
        local subNames = {
            "01_Downloads",
            "02_Video Clips",
            "03_Music & SFX",
            "04_Dialogue & Audio",
            "05_Proxies & Renders"
        }
        local existing = {}
        local xsubs = xdropRoot:GetSubFolderList() or {}
        for _, sf in ipairs(xsubs) do
            existing[sf:GetName()] = true
        end
        for _, sname in ipairs(subNames) do
            if not existing[sname] then
                mediaPool:AddSubFolder(xdropRoot, sname)
            end
        end
        return true
    end
    return false
end

-- =============================================================================
-- BACKGROUND ENGINE LIFECYCLE (Zero-Flicker)
-- =============================================================================

local function IsEngineOnline()
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
        local candidateVbs = {
            localAppData .. "\\Xdrop\\start_engine.vbs",
            userProfile .. "\\AppData\\Local\\Xdrop\\start_engine.vbs",
            userProfile .. "\\.xdrop\\start_engine.vbs",
        }

        for _, vbs in ipairs(candidateVbs) do
            if FileExists(vbs) then
                os.execute('wscript.exe //B "' .. vbs .. '"')
                return true
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
            os.execute('wscript.exe //B "' .. tempVbs .. '"')
            return true
        end
    else
        local home = os.getenv("HOME") or ""
        local sh = home .. "/.xdrop/run.sh"
        if FileExists(sh) then
            os.execute(sh .. " &")
        else
            os.execute("python3 -m xdrop.main --background &")
        end
        return true
    end
    return false
end

local function EnsureEngineRunning()
    if IsEngineOnline() then
        TouchSessionLease()
        return true
    end

    StartEngineBackground()

    -- Wait briefly for engine to respond
    for _ = 1, 15 do
        if bmd and bmd.wait then
            bmd.wait(0.2)
        end
        if IsEngineOnline() then
            TouchSessionLease()
            return true
        end
    end
    TouchSessionLease()
    return true
end

-- =============================================================================
-- STANDALONE APP WINDOW LAUNCHER (Unified React Studio UI)
-- =============================================================================

local function FindChromiumExecutable()
    if platform == "Windows" then
        local progFilesX86 = os.getenv("ProgramFiles(x86)") or "C:\\Program Files (x86)"
        local progFiles = os.getenv("ProgramFiles") or "C:\\Program Files"
        local localAppData = os.getenv("LOCALAPPDATA") or ""

        local candidates = {
            -- Microsoft Edge (Standard on Windows 10/11)
            progFilesX86 .. "\\Microsoft\\Edge\\Application\\msedge.exe",
            progFiles .. "\\Microsoft\\Edge\\Application\\msedge.exe",
            localAppData .. "\\Microsoft\\Edge\\Application\\msedge.exe",
            -- Google Chrome
            progFiles .. "\\Google\\Chrome\\Application\\chrome.exe",
            progFilesX86 .. "\\Google\\Chrome\\Application\\chrome.exe",
            localAppData .. "\\Google\\Chrome\\Application\\chrome.exe",
            -- Brave Browser
            progFiles .. "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            localAppData .. "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        }

        for _, exe in ipairs(candidates) do
            if FileExists(exe) then
                return exe
            end
        end
    elseif platform == "Mac" then
        local macCandidates = {
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        }
        for _, appPath in ipairs(macCandidates) do
            if FileExists(appPath) then
                return appPath
            end
        end
    else
        local linuxCandidates = {
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/microsoft-edge",
            "/usr/bin/brave-browser",
        }
        for _, bin in ipairs(linuxCandidates) do
            if FileExists(bin) then
                return bin
            end
        end
    end
    return nil
end

local function LaunchStudioApp()
    local browser = FindChromiumExecutable()

    if platform == "Windows" and browser then
        -- Launch standalone frameless application window with ZERO console flash
        local tempDir = os.getenv("TEMP") or os.getenv("TMP") or "C:\\Windows\\Temp"
        local launchVbs = tempDir .. "\\xdrop_launch_studio.vbs"
        local f = io.open(launchVbs, "w")
        if f then
            local cmd = string.format(
                '""%s"" --app=""%s"" --window-size=480,760 --app-id=Xdrop --disable-features=Translate --disable-default-apps',
                browser, SERVICE_URL
            )
            f:write('Set WshShell = CreateObject("WScript.Shell")\r\n')
            f:write(string.format('WshShell.Run "%s", 1, False\r\n', cmd))
            f:close()
            os.execute('wscript.exe //B "' .. launchVbs .. '"')
            return true
        end
    elseif platform == "Mac" and browser then
        local cmd = string.format('"%s" --app="%s" --window-size=480,760 &', browser, SERVICE_URL)
        os.execute(cmd)
        return true
    elseif platform == "Linux" and browser then
        local cmd = string.format('"%s" --app="%s" --window-size=480,760 &', browser, SERVICE_URL)
        os.execute(cmd)
        return true
    end

    -- Graceful fallback to default system browser
    if bmd and bmd.openurl then
        bmd.openurl(SERVICE_URL)
        return true
    elseif platform == "Windows" then
        os.execute('start "" "' .. SERVICE_URL .. '"')
        return true
    elseif platform == "Mac" then
        os.execute('open "' .. SERVICE_URL .. '"')
        return true
    else
        os.execute('xdg-open "' .. SERVICE_URL .. '" &')
        return true
    end
end

-- =============================================================================
-- MAIN ENTRYPOINT
-- =============================================================================

local function Main()
    -- 1. Setup Xdrop media pool bin structure
    pcall(SetupXdropBins)

    -- 2. Ensure background engine is running silently
    EnsureEngineRunning()

    -- 3. Touch active session lease
    TouchSessionLease()

    -- 4. Launch the unified modern React Studio UI window
    LaunchStudioApp()

    print("[Xdrop] Studio UI launched: " .. SERVICE_URL)
end

Main()
collectgarbage("collect")
