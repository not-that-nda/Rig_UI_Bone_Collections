bl_info = {
    "name": "AMP RIG UI",
    "blender": (4, 0, 0),
    "category": "Animation",
    "description": "UI to manage RIG UI in Blender",
    "author": "NotThatNDA",
    "version": (1, 0, 0),
    "doc_url": "https://discord.gg/Em7sa72H97",
    "tracker_url": "https://discord.gg/Em7sa72H97",
    "location": "View3D > Side Panel",
    "warning": "Alpha",
}

bl_info = {
    "name": "AniMate Pro",
    "author": "not that NDA",
    "description": "Modular collection of animation tools",
    "blender": (3, 6, 0),
    "version": (1, 2, 9),
    "location": "",
    "warning": "alpha",
    "doc_url": "",
    "tracker_url": "",
    "category": "Animation",
}

import bpy
import os

should_update = True


class rig_ui_OT_export_rig_ui(bpy.types.Operator):
    """Export Rig UI script"""

    bl_idname = "rig_ui.export_rig_ui"
    bl_label = "Export Rig UI"
    bl_options = {"REGISTER"}

    # Define the filepath property which will store the path to save the file
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        # Initialize the filepath
        armature = context.view_layer.objects.active
        self.filepath = os.path.join(
            bpy.path.abspath("//"), f"RigUI_{armature.name}.py"
        )

        # Open the file browser
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # Generate and write the script to the specified file
        armature = context.view_layer.objects.active
        script_content = self.generate_script(armature)

        with open(self.filepath, "w") as file:
            file.write(script_content)

        self.report({"INFO"}, f"Rig UI script exported to {self.filepath}")
        return {"FINISHED"}

    def generate_script(self, armature):
        panel_name = f"AMP_PT_RigUI_{armature.name.replace(' ', '_')}"  # Replace spaces with underscores for valid identifier
        script = f"""
import bpy

class {panel_name}(bpy.types.Panel):
    \"\"\"Panel for Rig UI\"\"\"
    bl_label = "Rig UI"
    bl_idname = "{panel_name}"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Rig'

    def draw(self, context):
        layout = self.layout
        armature = context.view_layer.objects.active

        if armature and armature.type == 'ARMATURE':
            ui_include_layers = [layer for layer in armature.data.collections.values() if layer.get('UI_include', False)]

            sorted_ui_include_layers = sorted(ui_include_layers, key=lambda l: (l.get('row', 0), -l.get('priority', 0), l.name))

            box = layout.box()
            layers_by_row = {{}}

            for layer in sorted_ui_include_layers:
                row_num = layer.get('row', 0)
                layers_by_row.setdefault(row_num, []).append(layer)

            for row_num in sorted(layers_by_row.keys()):
                row_layout = box.row()
                for layer in sorted(layers_by_row[row_num], key=lambda l: (-l.get('priority', 0), l.name)):
                    icon_name = layer.get('icon_name', 'NONE')
                    icon_name = 'NONE' if icon_name == 'BLANK1' else icon_name
                    display_text = layer.name if layer.get('display_name', False) else ''
                    row_layout.prop(layer, 'is_visible', text=display_text, icon=icon_name, toggle=True)

def register():
    bpy.utils.register_class({panel_name})

def unregister():
    bpy.utils.unregister_class({panel_name})

if __name__ == "__main__":
    register()
    """
        return script


class BoneLayerAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    rig_ui_setup_sidepanel: bpy.props.StringProperty(
        name="RIG UI Setup Side Panel", default="Animation"
    )

    rig_ui_sidepanel: bpy.props.StringProperty(
        name="RIG UI Side Panel", default="Animation"
    )

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__name__].preferences
        layout.prop(prefs, "rig_ui_setup_sidepanel")
        layout.prop(prefs, "rig_ui_sidepanel")
        layout.operator("rig_ui.update_side_panel_preferences")


# Operator to update the Side Panel preferences
class rig_ui_OT_UpdatesidepanelPreferences(bpy.types.Operator):
    bl_idname = "rig_ui.update_side_panel_preferences"
    bl_label = "Update Side Panel Preferences"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        unregister_panels()
        register_panels(prefs.rig_ui_setup_sidepanel, prefs.rig_ui_sidepanel)
        return {"FINISHED"}


def get_armatures(context):
    """Returns a list of armature objects in the current file."""
    armatures = [obj for obj in context.scene.objects if obj.type == "ARMATURE"]
    return armatures


def initialize_bone_layer_properties(armature):
    """Initializes bone layer properties for the given armature."""
    if armature and armature.type == "ARMATURE":
        armature.data.bone_layer_properties.clear()

        for layer in armature.data.collections.values():
            layer_props = armature.data.bone_layer_properties.add()
            layer_props.name = layer.name
            layer_props.UI_include = layer.get("UI_include", False)
            layer_props.row = max(layer.get("row", 1), 1)
            layer_props.priority = max(layer.get("priority", 1), 1)
            layer_props.display_name = layer.get("display_name", True)
            layer_props.icon_name = layer.get("icon_name", "BLANK")


def update_bone_layer_list(self, context):
    armature = context.view_layer.objects.active
    if armature and armature.type == "ARMATURE":
        # Initialize Side Panel_name if not present
        if "sidepanel_name" not in armature.data:
            armature.data["sidepanel_name"] = "Animation"

        # Update RIG UI based on current armature data
        update_rig_ui(armature)

        # Ensure all RIG UI have necessary properties
        for layer in armature.data.collections.values():
            if "UI_include" not in layer:
                layer["UI_include"] = False
            if "row" not in layer:
                layer["row"] = 1
            if "priority" not in layer:
                layer["priority"] = 1
            if "display_name" not in layer:
                layer["display_name"] = True
            if "icon_name" not in layer:
                layer["icon_name"] = "BLANK1"


def update_bone_layer_display_names(armature):
    """Updates display names to match actual bone layer names and initializes unique display name properties."""
    if armature and armature.type == "ARMATURE":
        for layer_props in armature.data.bone_layer_properties:
            bone_layer = armature.data.collections.get(layer_props.name)
            if bone_layer:
                unique_display_name_prop = f'["{layer_props.name}_display_name"]'
                if unique_display_name_prop not in bone_layer:
                    bone_layer[
                        unique_display_name_prop
                    ] = True  # Default value, change as needed


def update_rig_ui(armature):
    global should_update
    if not should_update or not armature or armature.type != "ARMATURE":
        return
    if armature and armature.type == "ARMATURE":
        should_update = False
        try:
            existing_layers = {
                layer.name: layer for layer in armature.data.collections.values()
            }

            # Sort layers with 'UI_include' on top, then by row (ascending) and priority (descending), then alphabetically
            sorted_layers = sorted(
                existing_layers.values(),
                key=lambda l: (
                    -l.get("UI_include", False),
                    l.get("row", 0),
                    -l.get("priority", 0),
                    l.name,
                ),
            )

            armature.data.bone_layer_properties.clear()
            for layer in sorted_layers:
                layer_props = armature.data.bone_layer_properties.add()
                layer_props.name = layer.name
                layer_props.row = layer.get("row", 0)
                layer_props.priority = layer.get("priority", 0)
        finally:
            should_update = True


class AMP_UL_BoneLayers(bpy.types.UIList):
    """UI List to display and edit bone layer properties."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        armature = context.view_layer.objects.active
        if armature and armature.type == "ARMATURE":
            # Ensure the bone layer is fetched correctly
            bone_layer = armature.data.collections.get(item.name)
            if bone_layer:
                # Main row for all elements
                row = layout.row(align=True)

                # Column for UI_include toggle
                ui_include_icon = (
                    "HIDE_OFF" if bone_layer.get("UI_include", False) else "HIDE_ON"
                )
                row.prop(bone_layer, '["UI_include"]', icon=ui_include_icon, text="")

                # Button to update icon from clipboard
                icon_op = row.operator("rig_ui.paste_icon", text="", icon="PASTEDOWN")
                icon_op.bone_layer_name = item.name

                # Set default icon to BLANK1 if not set or set to NONE
                selected_icon = bone_layer.get("icon_name", "BLANK1")
                selected_icon = "BLANK1" if selected_icon == "NONE" else selected_icon

                # Display the selected icon next to the button
                row.label(text="", icon=selected_icon)

                # Split for name, row, and priority
                split = row.split(factor=0.5, align=True)

                # Toggle for display_name with the actual name of the layer
                split.prop(bone_layer, '["display_name"]', text=item.name, toggle=True)

                sub_row = split.row(align=True)
                sub_row.prop(bone_layer, '["row"]', text="")
                sub_row.prop(bone_layer, '["priority"]', text="")


class rig_ui_OT_refresh_list(bpy.types.Operator):
    """Refresh RIG UI List"""

    bl_idname = "rig_ui.refresh_list"
    bl_label = "Refresh RIG UI List"

    def execute(self, context):
        armature = context.view_layer.objects.active
        if armature and armature.type == "ARMATURE":
            update_rig_ui(armature)
        return {"FINISHED"}


class AMP_PT_BoneLayersSetup(bpy.types.Panel):
    """Panel for managing RIG UI."""

    bl_label = "RIG UI Setup"
    bl_idname = "AMP_PT_BoneLayersSetup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        armature = context.view_layer.objects.active
        prefs = bpy.context.preferences.addons[__name__].preferences

        # Check if the active object is an armature
        if armature and armature.type == "ARMATURE":
            # Display edit mode toggle and list
            row = layout.row(align=True)
            row.prop(scene, "amp_edit_mode", toggle=True)
            if scene.amp_edit_mode:
                # Export button next to the refresh button
                row.operator("rig_ui.refresh_list", text="", icon="FILE_REFRESH")
                row.operator("rig_ui.export_rig_ui", text="", icon="EXPORT")

            # Check if Icon Viewer add-on is loaded
            if scene.amp_edit_mode:
                icon_viewer_loaded = (
                    "development_icon_get" in bpy.context.preferences.addons
                )
                if icon_viewer_loaded:
                    # Button to invoke Icon Viewer
                    layout.operator(
                        "iv.icons_show", text="Select Icon", icon="SEQ_PREVIEW"
                    )
                else:
                    # Button to load Icon Viewer
                    layout.operator(
                        "rig_ui.load_icon_viewer", text="Activate Icon Viewer"
                    )

            if scene.amp_edit_mode:
                # Draw bone layer list first
                draw_bone_layer_list(self, context)

                # Display armature name, sidepanel name field, and refresh button
                layout.label(text=armature.name)
                row = layout.row()
                row.prop(prefs, "rig_ui_sidepanel", text="Side Panel")
                row.operator(
                    "rig_ui.update_side_panel_preferences",
                    text="",
                    icon="FILE_REFRESH",
                )

            # Draw UI buttons for RIG UI
            ui_include_layers = any(
                layer.get("UI_include", False)
                for layer in armature.data.collections.values()
            )
            if ui_include_layers:
                draw_bone_layer_buttons(self, context)
            else:
                layout.label(text="Add RIG UI")
        else:
            layout.label(text="No Armature Selected.")


def draw_bone_layer_list(self, context):
    """Draws the bone layer property list in the panel."""
    layout = self.layout
    armature = context.view_layer.objects.active

    if armature and armature.type == "ARMATURE":
        # Simulating headers for the list
        row = layout.row()
        row.label(text="Include")
        row.label(text="Icon")
        row.label(text="Name")
        row.label(text="Row")
        row.label(text="Priority")

        row = layout.row()
        row.template_list(
            "AMP_UL_BoneLayers",
            "rig_ui",
            armature.data,
            "bone_layer_properties",
            armature.data,
            "active_bone_layer_index",
        )


def draw_bone_layer_buttons(self, context):
    """Draws buttons for RIG UI in normal mode."""
    layout = self.layout
    armature = context.view_layer.objects.active

    if armature and armature.type == "ARMATURE":
        ui_include_layers = [
            layer
            for layer in armature.data.collections.values()
            if layer.get("UI_include", False)
        ]

        sorted_ui_include_layers = sorted(
            ui_include_layers,
            key=lambda l: (l.get("row", 0), -l.get("priority", 0), l.name),
        )

        box = layout.box()
        layers_by_row = {}

        for layer in sorted_ui_include_layers:
            row_num = layer.get("row", 0)
            layers_by_row.setdefault(row_num, []).append(layer)

        for row_num in sorted(layers_by_row.keys()):
            row_layout = box.row()
            for layer in sorted(
                layers_by_row[row_num], key=lambda l: (-l.get("priority", 0), l.name)
            ):
                # Set icon to NONE if it is BLANK1
                icon_name = layer.get("icon_name", "NONE")
                icon_name = "NONE" if icon_name == "BLANK1" else icon_name

                display_text = layer.name if layer.get("display_name", False) else ""
                row_layout.prop(
                    layer, "is_visible", text=display_text, icon=icon_name, toggle=True
                )


def update_edit_mode(self, context):
    update_bone_layer_list(self, context)


# Operator to show the icon selector pop-up
class rig_ui_OT_paste_icon(bpy.types.Operator):
    bl_idname = "rig_ui.paste_icon"
    bl_label = "Update Icon from Clipboard"
    bl_options = {"REGISTER", "UNDO"}

    bone_layer_name: bpy.props.StringProperty()

    def execute(self, context):
        # Get the icon name from the clipboard
        clipboard_icon = context.window_manager.clipboard

        if not self.bone_layer_name:
            self.report({"ERROR"}, "No bone layer name specified")
            return {"CANCELLED"}

        # Check if the clipboard content is a valid icon name
        if (
            clipboard_icon
            in bpy.types.UILayout.bl_rna.functions["prop"]
            .parameters["icon"]
            .enum_items.keys()
        ):
            # Set or update the icon name to the bone layer
            bone_layer = context.object.data.collections[self.bone_layer_name]
            bone_layer["icon_name"] = clipboard_icon
            self.report(
                {"INFO"},
                f"Icon '{clipboard_icon}' updated for bone layer '{self.bone_layer_name}'",
            )
        else:
            self.report({"WARNING"}, "Clipboard does not contain a valid icon name")

        return {"FINISHED"}


# Operator to load Icon Viewer add-on
class rig_ui_OT_load_icon_viewer(bpy.types.Operator):
    """Load the Icon Viewer Add-on"""

    bl_idname = "rig_ui.load_icon_viewer"
    bl_label = "Load Icon Viewer"

    def execute(self, context):
        bpy.ops.preferences.addon_enable(module="development_icon_get")
        return {"FINISHED"}


class AMP_PT_BoneLayers(bpy.types.Panel):
    """Panel for displaying RIG UI."""

    bl_label = "RIG UI"
    bl_idname = "AMP_PT_BoneLayers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        armature = context.view_layer.objects.active

        if armature and armature.type == "ARMATURE":
            # Check if any layers have 'UI_include' set to True
            ui_include_layers = any(
                layer.get("UI_include", False)
                for layer in armature.data.collections.values()
            )

            if ui_include_layers:
                draw_bone_layer_buttons(self, context)
            else:
                layout.label(text="Add RIG UI")
        else:
            layout.label(text="No Armature Selected.")


# Functions to register/unregister panels with dynamic Side Panel names
def register_panels(setup_sidepanel_name, rig_ui_sidepanel_name):
    AMP_PT_BoneLayersSetup.bl_category = setup_sidepanel_name
    AMP_PT_BoneLayers.bl_category = rig_ui_sidepanel_name
    bpy.utils.register_class(AMP_PT_BoneLayersSetup)
    bpy.utils.register_class(AMP_PT_BoneLayers)


def unregister_panels():
    if bpy.utils.unregister_class(AMP_PT_BoneLayersSetup):
        bpy.utils.unregister_class(AMP_PT_BoneLayersSetup)
    if bpy.utils.unregister_class(AMP_PT_BoneLayers):
        bpy.utils.unregister_class(AMP_PT_BoneLayers)


# Operator to update the sidepanel for the RIG UI panel
class rig_ui_OT_Updatesidepanel(bpy.types.Operator):
    bl_idname = "rig_ui.update_sidepanel"
    bl_label = "Update sidepanel"

    def execute(self, context):
        armature = context.view_layer.objects.active
        if armature and armature.type == "ARMATURE":
            # Fetch sidepanel names from armature data
            setup_sidepanel_name = armature.data.get("sidepanel_name", "Animation")
            rig_ui_sidepanel_name = setup_sidepanel_name
            unregister_panels()
            register_panels(setup_sidepanel_name, rig_ui_sidepanel_name)
        return {"FINISHED"}


class BoneLayerProperties(bpy.types.PropertyGroup):
    """Property group for bone layer properties."""

    UI_include: bpy.props.BoolProperty(name="UI Include", default=False)
    row: bpy.props.IntProperty(
        name="Row", default=1, min=1, update=update_bone_layer_list
    )
    priority: bpy.props.IntProperty(
        name="Priority", default=1, min=1, update=update_bone_layer_list
    )
    selected_icon: bpy.props.StringProperty(name="Selected Icon", default="BLANK1")
    icon_name: bpy.props.StringProperty(name="Icon Name", default="BLANK1")
    display_name: bpy.props.BoolProperty(name="Display Name", default=True)
    bpy.types.Armature.sidepanel_name = bpy.props.StringProperty(
        name="sidepanel Name",
        description="Name of the sidepanel where the RIG UI panel will be displayed",
        default="Animation",
    )


def register():
    # Register classes
    bpy.utils.register_class(rig_ui_OT_export_rig_ui)
    bpy.utils.register_class(rig_ui_OT_UpdatesidepanelPreferences)
    bpy.utils.register_class(BoneLayerAddonPreferences)
    bpy.utils.register_class(rig_ui_OT_Updatesidepanel)
    bpy.utils.register_class(BoneLayerProperties)
    bpy.utils.register_class(AMP_UL_BoneLayers)
    bpy.utils.register_class(rig_ui_OT_refresh_list)
    bpy.utils.register_class(rig_ui_OT_load_icon_viewer)
    bpy.utils.register_class(rig_ui_OT_paste_icon)
    bpy.types.Armature.bone_layer_properties = bpy.props.CollectionProperty(
        type=BoneLayerProperties
    )

    # Initialize panels with default or stored sidepanel names
    prefs = bpy.context.preferences.addons[__name__].preferences

    register_panels(prefs.rig_ui_setup_sidepanel, prefs.rig_ui_sidepanel)

    bpy.types.Scene.amp_edit_mode = bpy.props.BoolProperty(
        name="Edit Mode", default=True, update=update_edit_mode
    )
    bpy.types.Armature.active_bone_layer_index = bpy.props.IntProperty()
    bpy.types.Scene.selected_bone_layer_name = bpy.props.StringProperty()


def unregister():
    bpy.utils.unregister_class(rig_ui_OT_export_rig_ui)
    bpy.utils.unregister_class(rig_ui_OT_UpdatesidepanelPreferences)
    bpy.utils.unregister_class(BoneLayerAddonPreferences)
    bpy.utils.unregister_class(rig_ui_OT_Updatesidepanel)
    bpy.utils.unregister_class(rig_ui_OT_load_icon_viewer)
    bpy.utils.unregister_class(rig_ui_OT_paste_icon)
    bpy.utils.unregister_class(rig_ui_OT_refresh_list)
    bpy.utils.unregister_class(BoneLayerProperties)
    bpy.utils.unregister_class(AMP_UL_BoneLayers)
    del bpy.types.Scene.selected_bone_layer_name
    del bpy.types.Scene.amp_edit_mode
    del bpy.types.Armature.active_bone_layer_index
    del bpy.types.Armature.bone_layer_properties
    unregister_panels()


if __name__ == "__main__":
    register()
