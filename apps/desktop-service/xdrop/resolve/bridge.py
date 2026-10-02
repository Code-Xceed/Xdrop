import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from xdrop.logger import resolve_logger, errors_logger

class ResolveBridge:
    """Official DaVinci Resolve Scripting API bridge."""

    def __init__(self):
        self._bmd = None
        self._initialized = False
        self._setup_environment()

    def _setup_environment(self) -> None:
        """Configures Python path for DaVinciResolveScript according to OS specifications."""
        try:
            if sys.platform.startswith("win"):
                programdata = os.getenv("PROGRAMDATA", "C:\\ProgramData")
                modules_path = os.path.join(
                    programdata,
                    "Blackmagic Design",
                    "DaVinci Resolve",
                    "Support",
                    "Developer",
                    "Scripting",
                    "Modules"
                )
                lib_path = "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll"
                if os.path.exists(lib_path):
                    os.environ["RESOLVE_SCRIPT_LIB"] = lib_path
            elif sys.platform.startswith("darwin"):
                modules_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
            else:
                modules_path = "/opt/resolve/Developer/Scripting/Modules"

            if os.path.exists(modules_path) and modules_path not in sys.path:
                sys.path.append(modules_path)

            try:
                import DaVinciResolveScript as bmd
                self._bmd = bmd
                self._initialized = True
                resolve_logger.info("Successfully loaded DaVinciResolveScript module.")
            except ImportError:
                # Try dynamic load fallback
                script_path = os.path.join(modules_path, "DaVinciResolveScript.py")
                if os.path.exists(script_path):
                    spec = importlib.util.spec_from_file_location("DaVinciResolveScript", script_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules["DaVinciResolveScript"] = module
                        spec.loader.exec_module(module)
                        self._bmd = module
                        self._initialized = True
                        resolve_logger.info("Dynamically loaded DaVinciResolveScript from fallback location.")
                else:
                    resolve_logger.warning(f"DaVinciResolveScript not found at: {modules_path}")
        except Exception as e:
            errors_logger.error(f"Error configuring DaVinci Resolve scripting environment: {e}")

    def get_resolve_app(self) -> Optional[Any]:
        """Returns the active Resolve application instance, or None if not running."""
        if not self._bmd:
            self._setup_environment()
        if not self._bmd:
            return None

        try:
            resolve = self._bmd.scriptapp("Resolve")
            return resolve
        except Exception as e:
            resolve_logger.debug(f"Unable to connect to Resolve scriptapp: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Returns detailed status of DaVinci Resolve connection and active project."""
        now = datetime.now(timezone.utc).isoformat()
        resolve = self.get_resolve_app()

        if not resolve:
            return {
                "isAvailable": False,
                "version": None,
                "productName": None,
                "currentProject": None,
                "currentTimeline": None,
                "mediaPoolFolder": None,
                "error": "DaVinci Resolve is not running. Xdrop will queue imports until Resolve is opened.",
                "lastChecked": now,
            }

        try:
            product_name = str(resolve.GetProductName())
            version_string = str(resolve.GetVersionString())
            project_manager = resolve.GetProjectManager()
            project = project_manager.GetCurrentProject() if project_manager else None

            project_name = project.GetName() if project else None
            timeline_name = None
            media_pool_folder_name = None

            if project:
                current_timeline = project.GetCurrentTimeline()
                if current_timeline:
                    timeline_name = current_timeline.GetName()

                media_pool = project.GetMediaPool()
                if media_pool:
                    root_folder = media_pool.GetRootFolder()
                    if root_folder:
                        media_pool_folder_name = root_folder.GetName()

            return {
                "isAvailable": True,
                "version": version_string,
                "productName": product_name,
                "currentProject": project_name,
                "currentTimeline": timeline_name,
                "mediaPoolFolder": media_pool_folder_name,
                "error": None if project_name else "DaVinci Resolve is open, but no project is currently loaded.",
                "lastChecked": now,
            }
        except Exception as e:
            errors_logger.error(f"Error querying DaVinci Resolve status: {e}")
            return {
                "isAvailable": False,
                "version": None,
                "productName": None,
                "currentProject": None,
                "currentTimeline": None,
                "mediaPoolFolder": None,
                "error": f"Error communicating with DaVinci Resolve: {str(e)}",
                "lastChecked": now,
            }

    def import_media(
        self,
        file_paths: List[str],
        target_bin_name: str = "Xdrop"
    ) -> Dict[str, Any]:
        """
        Imports specified file paths into the active DaVinci Resolve project's Media Pool.
        Creates or targets the specified folder/bin.
        """
        resolve = self.get_resolve_app()
        if not resolve:
            return {
                "success": False,
                "importedClips": [],
                "targetBin": target_bin_name,
                "error": "DaVinci Resolve is not running. Asset is saved locally and can be imported later."
            }

        try:
            project_manager = resolve.GetProjectManager()
            if not project_manager:
                return {"success": False, "error": "Unable to access Resolve ProjectManager."}

            project = project_manager.GetCurrentProject()
            if not project:
                return {
                    "success": False,
                    "error": "DaVinci Resolve has no open project. Open a project to import media."
                }

            media_pool = project.GetMediaPool()
            if not media_pool:
                return {"success": False, "error": "Unable to access Resolve MediaPool."}

            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                return {"success": False, "error": "Unable to access MediaPool RootFolder."}

            # Find or create target bin
            target_folder = self._find_or_create_subfolder(media_pool, root_folder, target_bin_name)
            if target_folder:
                media_pool.SetCurrentFolder(target_folder)
            else:
                media_pool.SetCurrentFolder(root_folder)

            # Validate input files exist
            valid_paths: List[str] = []
            for p in file_paths:
                resolved_p = str(Path(p).resolve())
                if os.path.isfile(resolved_p):
                    valid_paths.append(resolved_p)
                else:
                    resolve_logger.warning(f"File to import does not exist on disk: {resolved_p}")

            if not valid_paths:
                return {"success": False, "error": "None of the specified files exist on disk."}

            resolve_logger.info(f"Importing {len(valid_paths)} files into Resolve bin '{target_bin_name}': {valid_paths}")
            imported_items = media_pool.ImportMedia(valid_paths)

            if imported_items and len(imported_items) > 0:
                clip_names = []
                for item in imported_items:
                    try:
                        clip_names.append(item.GetName())
                    except Exception:
                        clip_names.append("Imported Clip")

                resolve_logger.info(f"Successfully imported {len(clip_names)} clips into Resolve: {clip_names}")
                return {
                    "success": True,
                    "clipName": clip_names[0] if clip_names else None,
                    "allClips": clip_names,
                    "targetBin": target_bin_name,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": "DaVinci Resolve MediaPool.ImportMedia returned no clips. Verify codec compatibility."
                }

        except Exception as e:
            errors_logger.error(f"Exception during Resolve MediaPool import: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"DaVinci Resolve import exception: {str(e)}"
            }

    def _find_or_create_subfolder(self, media_pool: Any, parent_folder: Any, target_name: str) -> Any:
        """Finds or creates a subfolder by name within a parent MediaPool folder."""
        try:
            subfolders = parent_folder.GetSubFolderList()
            if subfolders:
                for sf in subfolders:
                    if sf.GetName().lower() == target_name.lower():
                        return sf
            
            # Create if not found
            new_folder = media_pool.AddSubFolder(parent_folder, target_name)
            return new_folder or parent_folder
        except Exception as e:
            resolve_logger.warning(f"Error navigating/creating MediaPool folder '{target_name}': {e}")
            return parent_folder

# Singleton bridge instance
_bridge_instance: Optional[ResolveBridge] = None

def get_resolve_bridge() -> ResolveBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ResolveBridge()
    return _bridge_instance
