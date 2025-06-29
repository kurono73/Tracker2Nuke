# tracker2nuke
# Original Author: masahiro teraoka (from the "tracking2nukeTracker" addon)

import bpy
import re

NUKE_LENS_DISTORTION_TPL = """set cut_paste_input [stack 0]
version 14.0 v2
push $cut_paste_input
LensDistortion2 {{
 distortionDenominator0 {{{k1}}}
 distortionDenominator1 {{{k2}}}
 output Undistort
 name {node_name}
 selected true
}}"""

# ------------------------
# Tracker Export Logic
# ------------------------

def trackerNodeBuilder(name, data):
    """
    Builds a Nuke Tracker node script string from the given track data.

    Args:
        name (str): The base name for the Nuke node.
        data (dict): A dictionary containing track names and their marker data.

    Returns:
        str: The fully formatted Nuke Tracker node script.
    """
    # Nuke Tracker node header template
    # The number of tracks is dynamically inserted.
    node_header = f"""Tracker4 {{
 tracks {{ {{ 1 31 {len(data)} }}
  {{ {{ 5 1 20 enable e 1 }}
  {{ 3 1 75 name name 1 }}
  {{ 2 1 58 track_x track_x 1 }}
  {{ 2 1 58 track_y track_y 1 }}
  {{ 2 1 63 offset_x offset_x 1 }}
  {{ 2 1 63 offset_y offset_y 1 }}
  {{ 4 1 27 T T 1 }}
  {{ 4 1 27 R R 1 }}
  {{ 4 1 27 S S 1 }}
  {{ 2 0 45 error error 1 }}
  {{ 1 1 0 error_min error_min 1 }}
  {{ 1 1 0 error_max error_max 1 }}
  {{ 1 1 0 pattern_x pattern_x 1 }}
  {{ 1 1 0 pattern_y pattern_y 1 }}
  {{ 1 1 0 pattern_r pattern_r 1 }}
  {{ 1 1 0 pattern_t pattern_t 1 }}
  {{ 1 1 0 search_x search_x 1 }}
  {{ 1 1 0 search_y search_y 1 }}
  {{ 1 1 0 search_r search_r 1 }}
  {{ 1 1 0 search_t search_t 1 }}
  {{ 2 1 0 key_track key_track 1 }}
  {{ 2 1 0 key_search_x key_search_x 1 }}
  {{ 2 1 0 key_search_y key_search_y 1 }}
  {{ 2 1 0 key_search_r key_search_r 1 }}
  {{ 2 1 0 key_search_t key_search_t 1 }}
  {{ 2 1 0 key_track_x key_track_x 1 }}
  {{ 2 1 0 key_track_y key_track_y 1 }}
  {{ 2 1 0 key_track_r key_track_r 1 }}
  {{ 2 1 0 key_track_t key_track_t 1 }}
  {{ 2 1 0 key_centre_offset_x key_centre_offset_x 1 }}
  {{ 2 1 0 key_centre_offset_y key_centre_offset_y 1 }}
 }}
 {{
"""
    # Nuke Tracker node footer template
    # The node name is dynamically inserted.
    sanitized_name = name.replace(' ', '_').replace('.', '_')
    node_footer = f"""}}
}}
name trackerFromBlender_{sanitized_name}
}}
"""
    track_data_strings = []

    for track_name, frames_data in data.items():
        if not frames_data:
            continue
        
        sorted_frames = sorted(frames_data.keys())
        if not sorted_frames:
            continue
            
        first_frame = sorted_frames[0]
        
        x_curve = ' '.join(f'x{f} {frames_data[f][0]}' for f in sorted_frames)
        y_curve = ' '.join(f'x{f} {frames_data[f][1]}' for f in sorted_frames)
        
        # A template for a single track's data row
        track_string = f"""  {{ {{curve K x{first_frame} 1}} "{track_name}" {{curve {x_curve}}} {{curve {y_curve}}} {{curve K x{first_frame} 0}} {{curve K x{first_frame} 0}} 1 1 1 {{curve x{first_frame} 0}} 1 0 -32 -32 32 32 -22 -22 22 22 {{}} {{}}  {{}}  {{}}  {{}}  {{}}  {{}}  {{}}  {{}}  {{}}  {{}}   }}
"""
        track_data_strings.append(track_string)

    return node_header + "".join(track_data_strings) + node_footer

def clipSeparator(trackerDict):
    """
    Generates Nuke Tracker node scripts for each entry in the dictionary.

    Args:
        trackerDict (dict): A dictionary where keys are node names and values are track data.

    Returns:
        str: A concatenated string of all generated Nuke node scripts.
    """
    return ''.join(trackerNodeBuilder(k, v) for k, v in trackerDict.items() if v)

def copyClipBoard(nodes):
    """
    Copies the given string to the system clipboard via Blender's window manager.

    Args:
        nodes (str): The string to be copied.
    """
    bpy.context.window_manager.clipboard = nodes

def get_active_tracking_object(context):
    """
    Retrieves the active tracking object from the Clip Editor context.

    Args:
        context: The current Blender context.

    Returns:
        bpy.types.MovieClipTrackingObject or None: The active tracking object, or None if not found.
    """
    if context.space_data and context.space_data.type == 'CLIP_EDITOR' and context.space_data.clip:
        clip = context.space_data.clip
        tracking = clip.tracking
        index = tracking.active_object_index
        if 0 <= index < len(tracking.objects):
            return tracking.objects[index]
    return None

def assemble_tracker_data(context, select=False):
    """
    Assembles tracking data from the active object, generates a Nuke script,
    and copies it to the clipboard.

    Args:
        context: The current Blender context.
        select (bool): If True, export only selected tracks. Otherwise, export all.

    Returns:
        tuple[str, str]: A tuple containing the report message and its level ('INFO', 'WARNING').
    """
    clip = context.space_data.clip
    tracking_object = get_active_tracking_object(context)
    if not clip or not tracking_object:
        return "No active clip or tracking object.", 'WARNING'

    trackers = tracking_object.tracks
    trackerDict = {}
    tempdict = {}
    for t in trackers:
        if (select and not t.select) or not t.markers:
            continue
        pointdict = {}
        for m in t.markers:
            frame = m.frame + clip.frame_start - 1
            x = m.co[0] * clip.size[0]
            y = m.co[1] * clip.size[1]
            pointdict[frame] = [x, y]
        if pointdict:
            tempdict[t.name] = pointdict
            
    if not tempdict:
        return ("No tracks selected or selected tracks have no markers." if select
                else f"'{tracking_object.name}' has no tracks with markers."), 'INFO'

    trackerDict[tracking_object.name] = tempdict
    nodes = clipSeparator(trackerDict)
    if not nodes:
        return "Could not generate valid track data.", 'WARNING'

    copyClipBoard(nodes)
    track_count = sum(len(tracks) for tracks in trackerDict.values())
    return f"Exported {track_count} track(s) from '{tracking_object.name}' to clipboard.", 'INFO'

# ------------------------
# Operators
# ------------------------

class NUKE_OT_ExportAllTracks(bpy.types.Operator):
    """Operator to export all tracks of the active object to a Nuke Tracker node"""
    bl_idname = "clip.nuke_export_all"
    bl_label = "Export All Tracks"
    bl_description = "Copies all tracks of the active object to the clipboard as a Nuke Tracker node"
    
    @classmethod
    def poll(cls, context):
        return get_active_tracking_object(context) is not None

    def execute(self, context):
        msg, level = assemble_tracker_data(context, select=False)
        self.report({level}, msg)
        return {'FINISHED'}

class NUKE_OT_ExportSelectedTracks(bpy.types.Operator):
    """Operator to export only the selected tracks of the active object to a Nuke Tracker node"""
    bl_idname = "clip.nuke_export_selected"
    bl_label = "Export Selected Tracks"
    bl_description = "Copies only the selected tracks of the active object to the clipboard as a Nuke Tracker node"

    @classmethod
    def poll(cls, context):
        tracking_object = get_active_tracking_object(context)
        if not tracking_object:
            return False
        return any(t.select for t in tracking_object.tracks)

    def execute(self, context):
        msg, level = assemble_tracker_data(context, select=True)
        self.report({level}, msg)
        return {'FINISHED'}

class NUKE_OT_ExportPatternCorners(bpy.types.Operator):
    """Operator to export the four corners of a selected track's pattern as four separate tracks"""
    bl_idname = "clip.nuke_export_pattern_corners"
    bl_label = "Export Pattern Corners"
    bl_description = "Exports the four corners of the selected track's pattern boundary as four separate tracks"

    @classmethod
    def poll(cls, context):
        tracking_object = get_active_tracking_object(context)
        if not tracking_object:
            return False
        # Check if exactly one track is selected
        return sum(1 for t in tracking_object.tracks if t.select) == 1

    def execute(self, context):
        clip = context.space_data.clip
        tracking_object = get_active_tracking_object(context)
        selected_tracks = [t for t in tracking_object.tracks if t.select]
        
        # This check is redundant due to poll, but good for safety
        if len(selected_tracks) != 1:
            self.report({'WARNING'}, "Please select exactly one track.")
            return {'CANCELLED'}
            
        track = selected_tracks[0]
        if not track.markers:
            self.report({'INFO'}, f"Track '{track.name}' has no markers.")
            return {'CANCELLED'}
            
        corners = {f"{track.name}_corner{i+1}": {} for i in range(4)}
        for m in track.markers:
            frame = m.frame + clip.frame_start - 1
            center_x = m.co[0] * clip.size[0]
            center_y = m.co[1] * clip.size[1]
            for i, offset in enumerate(m.pattern_corners):
                # pattern_corners are relative to the center (m.co) and normalized
                px = offset[0] * clip.size[0]
                py = offset[1] * clip.size[1]
                corners[f"{track.name}_corner{i+1}"][frame] = (center_x + px, center_y + py)
                
        node_name = f"{tracking_object.name}_{track.name}"
        nodes = clipSeparator({node_name: corners})
        copyClipBoard(nodes)
        self.report({'INFO'}, f"Exported 4 pattern corners from '{track.name}'.")
        return {'FINISHED'}

class NUKE_OT_ExportPlaneTrack(bpy.types.Operator):
    """Operator to export the four corners of the active plane track as four separate tracks"""
    bl_idname = "clip.nuke_export_plane_track"
    bl_label = "Export Plane Track"
    bl_description = "Exports the four corners of the active plane track as four separate tracks"

    @classmethod
    def poll(cls, context):
        active_object = get_active_tracking_object(context)
        if not active_object:
            return False
        return active_object.plane_tracks.active is not None

    def execute(self, context):
        clip = context.space_data.clip
        active_object = get_active_tracking_object(context)
        
        # This check is mostly handled by poll(), but good practice.
        if not active_object:
            self.report({'WARNING'}, "Cannot find an active tracking object.")
            return {'CANCELLED'}

        plane_track = active_object.plane_tracks.active
        if not plane_track or not plane_track.markers:
            self.report({'INFO'}, "No valid plane track selected or it has no markers.")
            return {'CANCELLED'}
            
        corners = {f"{plane_track.name}_corner{i+1}": {} for i in range(4)}
        for pm in plane_track.markers:
            frame = pm.frame + clip.frame_start - 1
            if len(pm.corners) != 4:
                continue
            for i, c in enumerate(pm.corners):
                px = c[0] * clip.size[0]
                py = c[1] * clip.size[1]
                corners[f"{plane_track.name}_corner{i+1}"][frame] = (px, py)
        
        node_name = f"{active_object.name}_{plane_track.name}"
        nodes = clipSeparator({node_name: corners})
        copyClipBoard(nodes)
        self.report({'INFO'}, f"Exported plane track '{plane_track.name}'.")
        return {'FINISHED'}

class NUKE_OT_CopyDistortion(bpy.types.Operator):
    """Operator to copy camera distortion to the clipboard as a Nuke LensDistortion node"""
    bl_idname = "clip.nuke_copy_distortion"
    bl_label = "Copy Distortion"
    bl_description = "Copies Blender's camera distortion parameters to the clipboard as a Nuke LensDistortion node"

    @classmethod
    def poll(cls, context):
        return bool(context.space_data and context.space_data.type == 'CLIP_EDITOR' and context.space_data.clip)

    def execute(self, context):
        clip = context.space_data.clip
        cam = clip.tracking.camera
        if cam.distortion_model != 'NUKE':
            self.report({'WARNING'}, "Distortion model must be 'NUKE'. Change it in Camera Properties > Lens.")
            return {'CANCELLED'}
            
        k1, k2 = cam.nuke_k1, cam.nuke_k2
        name = f"{clip.name.split('.')[0]}_{cam.focal_length:.0f}mm"
        script = NUKE_LENS_DISTORTION_TPL.format(k1=k1, k2=k2, node_name=name)
        copyClipBoard(script)
        self.report({'INFO'}, "Copied lens distortion to clipboard.")
        return {'FINISHED'}

class NUKE_OT_PasteDistortion(bpy.types.Operator):
    """Operator to paste a Nuke LensDistortion node from the clipboard to the camera"""
    bl_idname = "clip.nuke_paste_distortion"
    bl_label = "Paste Distortion"
    bl_description = "Applies Nuke LensDistortion node information from the clipboard to the Blender camera"

    @classmethod
    def poll(cls, context):
        # Check if there is something in the clipboard and we are in the clip editor
        return bool(context.window_manager.clipboard and 
                    context.space_data and 
                    context.space_data.type == 'CLIP_EDITOR' and 
                    context.space_data.clip)

    def execute(self, context):
        clip = context.space_data.clip
        cam = clip.tracking.camera
        text = bpy.context.window_manager.clipboard
        
        # Use regex to find k1 and k2 values from the Nuke script
        k1_match = re.search(r"distortionDenominator0\s+([-\d.]+)", text)
        k2_match = re.search(r"distortionDenominator1\s+([-\d.]+)", text)
        
        if not (k1_match and k2_match):
            self.report({'WARNING'}, "Clipboard does not contain a valid Nuke LensDistortion node.")
            return {'CANCELLED'}
            
        cam.distortion_model = 'NUKE'
        cam.nuke_k1 = float(k1_match.group(1))
        cam.nuke_k2 = float(k2_match.group(1))
        self.report({'INFO'}, f"Pasted distortion K1={cam.nuke_k1:.4f}, K2={cam.nuke_k2:.4f}.")
        return {'FINISHED'}

# ------------------------
# UI
# ------------------------

class NUKE_PT_bridge_panel(bpy.types.Panel):
    """UI Panel in the Clip Editor for the Tracker to Nuke bridge"""
    bl_label = "Tracker to Nuke"
    bl_idname = "NUKE_PT_bridge_panel"
    bl_space_type = 'CLIP_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Track'

    @classmethod
    def poll(cls, context):
        return context.space_data.clip is not None

    def draw(self, context):
        layout = self.layout
        
        tracker_box = layout.box()
        tracker_box.label(text="Tracker Export")
        row = tracker_box.row(align=True)
        row.operator("clip.nuke_export_all", text="All")
        row.operator("clip.nuke_export_selected", text="Selected")
        tracker_box.operator("clip.nuke_export_pattern_corners")
        tracker_box.operator("clip.nuke_export_plane_track")
        
        layout.separator()
        
        distortion_box = layout.box()
        distortion_box.label(text="Lens Distortion")
        row = distortion_box.row(align=True)
        row.operator("clip.nuke_copy_distortion", text="Copy")
        row.operator("clip.nuke_paste_distortion", text="Paste")

class NUKE_MT_export_submenu(bpy.types.Menu):
    """Submenu for Nuke export options within the main 'Track' menu"""
    bl_idname = "NUKE_MT_export_submenu"
    bl_label = "Tracker to Nuke Export"

    def draw(self, context):
        layout = self.layout
        layout.operator(NUKE_OT_ExportAllTracks.bl_idname, text="All Tracks")
        layout.operator(NUKE_OT_ExportSelectedTracks.bl_idname, text="Selected Tracks")
        layout.separator()
        layout.operator(NUKE_OT_ExportPatternCorners.bl_idname)
        layout.operator(NUKE_OT_ExportPlaneTrack.bl_idname)

def draw_track_menu_items(self, context):
    """Draws the menu items to be appended to the CLIP_MT_track menu."""
    layout = self.layout
    layout.separator()
    layout.menu(NUKE_MT_export_submenu.bl_idname)
    layout.separator()

# ------------------------
# Registration
# ------------------------

classes = (
    NUKE_OT_ExportAllTracks,
    NUKE_OT_ExportSelectedTracks,
    NUKE_OT_ExportPatternCorners,
    NUKE_OT_ExportPlaneTrack,
    NUKE_OT_CopyDistortion,
    NUKE_OT_PasteDistortion,
    NUKE_PT_bridge_panel,
    NUKE_MT_export_submenu,
)

def register():
    """Registers all addon classes and adds menu items."""
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.CLIP_MT_track.append(draw_track_menu_items)

def unregister():
    """Unregisters all addon classes and removes menu items."""
    bpy.types.CLIP_MT_track.remove(draw_track_menu_items)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()