"""
Xdrop for Blender — Native Video Sequence Editor (VSE) Addon
Installs directly into Blender: Edit -> Preferences -> Add-ons -> Install...

Bridges Xdrop downloads directly into the active Blender Sequencer timeline
at the current playhead frame.
"""

bl_info = {
    "name": "Xdrop for Blender",
    "author": "Xdrop Team",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Sequencer > Sidebar > Xdrop",
    "description": "Universal Media Importer integration for Blender Video Sequence Editor",
    "category": "Sequencer",
}

import bpy
import json
import urllib.request
import urllib.error
from pathlib import Path


class XDROP_OT_CheckService(bpy.types.Operator):
    """Check connection to local Xdrop engine"""
    bl_idname = "xdrop.check_service"
    bl_label = "Check Xdrop Status"

    def execute(self, context):
        try:
            req = urllib.request.Request("http://127.0.0.1:8484/api/health", headers={"User-Agent": "Blender-Xdrop"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode())
                self.report({'INFO'}, f"Connected to Xdrop v{data.get('version', '1.0.0')}")
        except Exception as e:
            self.report({'ERROR'}, f"Could not connect to Xdrop service: {e}")
        return {'FINISHED'}


class XDROP_OT_ImportLatest(bpy.types.Operator):
    """Import latest completed Xdrop asset to active sequencer frame"""
    bl_idname = "xdrop.import_latest"
    bl_label = "Import Latest to Timeline"

    def execute(self, context):
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        seq = scene.sequence_editor

        try:
            req = urllib.request.Request("http://127.0.0.1:8484/api/downloads", headers={"User-Agent": "Blender-Xdrop"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                jobs = json.loads(resp.read().decode())

            completed = [j for j in jobs if j.get("status") == "completed" and j.get("output_file_path")]
            if not completed:
                self.report({'WARNING'}, "No completed downloads found in Xdrop queue.")
                return {'CANCELLED'}

            latest = completed[0]
            file_path = latest["output_file_path"]
            title = latest.get("title", Path(file_path).stem)

            if not Path(file_path).exists():
                self.report({'ERROR'}, f"File does not exist on disk: {file_path}")
                return {'CANCELLED'}

            frame_current = scene.frame_current

            # Determine available channel (track)
            used_channels = [s.channel for s in seq.sequences_all]
            target_channel = 1
            while target_channel in used_channels:
                target_channel += 1

            p = Path(file_path)
            ext = p.suffix.lower()

            if ext in ('.mp4', '.mov', '.mkv', '.webm', '.avi'):
                strip = seq.sequences.new_movie(
                    name=title,
                    filepath=file_path,
                    channel=target_channel,
                    frame_start=frame_current,
                )
                self.report({'INFO'}, f"Imported movie strip: {strip.name} to channel {target_channel}")
            elif ext in ('.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'):
                strip = seq.sequences.new_sound(
                    name=title,
                    filepath=file_path,
                    channel=target_channel,
                    frame_start=frame_current,
                )
                self.report({'INFO'}, f"Imported sound strip: {strip.name} to channel {target_channel}")
            elif ext in ('.png', '.jpg', '.jpeg', '.webp'):
                strip = seq.sequences.new_image(
                    name=title,
                    filepath=file_path,
                    channel=target_channel,
                    frame_start=frame_current,
                )
                strip.frame_final_duration = 120  # 4-5 seconds default
                self.report({'INFO'}, f"Imported image strip: {strip.name}")
            else:
                self.report({'WARNING'}, f"Unsupported format for Blender Sequencer: {ext}")
                return {'CANCELLED'}

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import from Xdrop: {e}")
            return {'CANCELLED'}


class XDROP_PT_Panel(bpy.types.Panel):
    """Xdrop Sidebar Panel in Video Sequence Editor"""
    bl_label = "Xdrop"
    bl_idname = "XDROP_PT_panel"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Xdrop"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Universal Media Importer", icon='COLORSET_01_VEC')
        col.separator()
        col.operator("xdrop.check_service", text="Check Service", icon='URL')
        col.separator()
        col.operator("xdrop.import_latest", text="Drop Latest to Timeline", icon='PLAY')


classes = (
    XDROP_OT_CheckService,
    XDROP_OT_ImportLatest,
    XDROP_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
