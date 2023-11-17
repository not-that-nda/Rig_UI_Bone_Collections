bl_info = {
    "name": "AMP RIG UI",
    "blender": (4, 0, 0),
    "category": "Animation",
    "description": "UI to manage RIG UI in Blender",
    "author": "NotThatNDA",
    "version": (1, 0, 4),
    "doc_url": "https://discord.gg/Em7sa72H97",
    "tracker_url": "https://discord.gg/Em7sa72H97",
    "location": "View3D > Side Panel",
    "warning": "Alpha",
}


import bpy
import os

rig_ui_should_update = True
rig_ui_popup_instance = None


# Array property type for storing recent icons
def get_recent_icons(self):
    return self.get("recent_icons", "")


def set_recent_icons(self, value):
    if isinstance(value, list):
        self["recent_icons"] = ",".join(value)
    elif isinstance(value, str):
        self["recent_icons"] = value
    else:
        self["recent_icons"] = ""


class RIG_UI_OT_IconSelector(bpy.types.Operator):
    bl_idname = "rig_ui.icon_selector"
    bl_label = ""
    bl_options = {"REGISTER", "UNDO"}

    # Define the bone_collection_name property
    bone_collection_name: bpy.props.StringProperty()

    # Define the filter_text property
    filter_text: bpy.props.StringProperty(
        name="Filter", description="Filter icons by name"
    )

    all_icons = (
        bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()
    )

    def invoke(self, context, event):
        global rig_ui_popup_instance
        rig_ui_popup_instance = self
        # Check modifier keys and set icon accordingly
        if event.alt:
            self.set_icon_directly(context, "BLANK1")
            return {"FINISHED"}
        elif event.shift or event.ctrl or event.oskey:  # oskey is for CMD on macOS
            clipboard_icon = context.window_manager.clipboard
            if clipboard_icon in self.all_icons:
                self.set_icon_directly(context, clipboard_icon)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, "Clipboard does not contain a valid icon name")
                return {"CANCELLED"}

        # Open the popup normally if no modifier key is pressed
        return context.window_manager.invoke_props_dialog(self, width=820)

    def filter_icons(self):
        # Use the filter_text property for filtering
        filter_lower = self.filter_text.lower()
        return [icon for icon in self.all_icons if filter_lower in icon.lower()]

    def draw(self, context):
        self.draw_ui(context)

    def draw_ui(self, context):
        layout = self.layout
        scene = context.scene

        # Filter field with VIEWZOOM icon
        filter_row = layout.row()
        filter_row.prop(self, "filter_text", text="", icon="VIEWZOOM")

        # Recent Icons Section
        recent_icons_box = layout.box()
        recent_icons_box.alignment = "CENTER"
        recent_row = recent_icons_box.row(align=True)
        recent_row.alignment = "CENTER"
        recent_icons = scene.recent_icons.split(",")[-20:] if scene.recent_icons else []
        for icon in recent_icons:
            if icon and icon in self.all_icons:
                icon_button = recent_row.operator(
                    "rig_ui.apply_icon", text="", icon=icon, emboss=False
                )
                icon_button.icon_name = icon
                icon_button.bone_collection_name = self.bone_collection_name
                icon_button.modifier_key = "NONE"

        # All Icons Section
        all_icons_box = layout.box()
        all_col = all_icons_box.column(align=True)
        filtered_icons = self.filter_icons()
        row = None
        for i, icon in enumerate(filtered_icons):
            if icon == "NONE":
                continue
            if i % 40 == 0 or row is None:
                row = all_col.row(align=True)
                row.alignment = "CENTER"
            # Change to use a method call or custom operator
            icon_button = row.operator(
                "rig_ui.apply_icon", text="", icon=icon, emboss=False
            )
            icon_button.bone_collection_name = self.bone_collection_name
            icon_button.icon_name = icon
            icon_button.modifier_key = "NONE"

    def execute(self, context):
        # This operator only opens the dialog, actual icon setting is handled in another operator
        return {"FINISHED"}

    def set_icon_directly(self, context, icon_name):
        # Logic to set the icon directly without opening the popup
        bone_collection = context.object.data.collections.get(self.bone_collection_name)
        if bone_collection:
            bone_collection["icon_name"] = icon_name
            update_recent_icons(context, icon_name)
        else:
            self.report({"ERROR"}, "Invalid bone collection name")
            return {"CANCELLED"}

    def refresh_ui(self, context):
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()


class RIG_UI_OT_ApplyIcon(bpy.types.Operator):
    bl_idname = "rig_ui.apply_icon"
    bl_label = "Apply Icon"
    bl_options = {"REGISTER", "UNDO"}

    icon_name: bpy.props.StringProperty()
    bone_collection_name: bpy.props.StringProperty()
    modifier_key: bpy.props.StringProperty(default="NONE")

    def execute(self, context):
        # Logic previously in set_icon_from_popup
        # Check the modifier key and set icon accordingly
        if self.modifier_key == "ALT":
            self.icon_name = "BLANK1"
        elif self.modifier_key in ["SHIFT", "CTRL", "CMD"]:
            clipboard_icon = context.window_manager.clipboard
            if clipboard_icon in RIG_UI_OT_IconSelector.all_icons:
                self.icon_name = clipboard_icon
            else:
                self.report({"WARNING"}, "Clipboard does not contain a valid icon name")
                return {"CANCELLED"}

        # Set the icon to the bone collection
        bone_collection = context.object.data.collections.get(self.bone_collection_name)
        if bone_collection:
            bone_collection["icon_name"] = self.icon_name
            update_recent_icons(context, self.icon_name)

            # Copy icon name to the clipboard
            context.window_manager.clipboard = self.icon_name

            # Report that the icon has been set
            self.report(
                {"INFO"},
                f"{self.bone_collection_name}'s icon has been set to {self.icon_name}",
            )

            context.area.tag_redraw()  # Refresh the UI
            self.close_popup(context)
            return {"FINISHED"}  # Signal that the operation is complete
        else:
            self.report({"ERROR"}, "Invalid bone collection name")
            return {"CANCELLED"}

    def close_popup(self, context):
        global rig_ui_popup_instance
        if rig_ui_popup_instance:
            bpy.context.window.screen = bpy.context.window.screen
            rig_ui_popup_instance = None


def update_recent_icons(context, icon_name):
    recent_icons = (
        context.scene.recent_icons.split(",") if context.scene.recent_icons else []
    )
    if icon_name not in recent_icons:
        recent_icons.append(icon_name)
        if len(recent_icons) > 20:
            recent_icons.pop(0)
    context.scene.recent_icons = ",".join(recent_icons)


class RIG_UI_OT_ExportToScript(bpy.types.Operator):
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
        panel_name = f"RIG_UI_PT_RigUI_{armature.name.replace(' ', '_')}"  # Replace spaces with underscores for valid identifier
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
            ui_include_collections = [collection for collection in armature.data.collections.values() if collection.get('UI_include', False)]

            sorted_ui_include_collections = sorted(ui_include_collections, key=lambda l: (l.get('row', 0), -l.get('priority', 0), l.name))

            box = layout.box()
            collections_by_row = {{}}

            for collection in sorted_ui_include_collections:
                row_num = collection.get('row', 0)
                collections_by_row.setdefault(row_num, []).append(collection)

            for row_num in sorted(collections_by_row.keys()):
                row_layout = box.row()
                for collection in sorted(collections_by_row[row_num], key=lambda l: (-l.get('priority', 0), l.name)):
                    icon_name = collection.get('icon_name', 'NONE')
                    icon_name = 'NONE' if icon_name == 'BLANK1' else icon_name
                    display_text = collection.name if collection.get('display_name', False) else ''
                    row_layout.prop(collection, 'is_visible', text=display_text, icon=icon_name, toggle=True)

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
class RIG_UI_OT_UpdateSidePanelPreferences(bpy.types.Operator):
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


def initialize_bone_collection_properties(armature):
    """Initializes bone collection properties for the given armature."""
    if armature and armature.type == "ARMATURE":
        armature.data.bone_collection_properties.clear()

        for collection in armature.data.collections.values():
            collection_props = armature.data.bone_collection_properties.add()
            collection_props.name = collection.name
            collection_props.UI_include = collection.get("UI_include", False)
            collection_props.row = max(collection.get("row", 1), 1)
            collection_props.priority = max(collection.get("priority", 1), 1)
            collection_props.display_name = collection.get("display_name", True)
            collection_props.icon_name = collection.get("icon_name", "BLANK")


def update_bone_collection_list(self, context):
    armature = context.view_layer.objects.active
    if armature and armature.type == "ARMATURE":
        # Initialize Side Panel_name if not present
        if "sidepanel_name" not in armature.data:
            armature.data["sidepanel_name"] = "Animation"

        # Update RIG UI based on current armature data
        update_rig_ui(armature)

        # Ensure all RIG UI have necessary properties
        for collection in armature.data.collections.values():
            if "UI_include" not in collection:
                collection["UI_include"] = False
            if "row" not in collection:
                collection["row"] = 1
            if "priority" not in collection:
                collection["priority"] = 1
            if "display_name" not in collection:
                collection["display_name"] = True
            if "icon_name" not in collection:
                collection["icon_name"] = "BLANK1"


def update_bone_collection_display_names(armature):
    """Updates display names to match actual bone collection names and initializes unique display name properties."""
    if armature and armature.type == "ARMATURE":
        for collection_props in armature.data.bone_collection_properties:
            bone_collection = armature.data.collections.get(collection_props.name)
            if bone_collection:
                unique_display_name_prop = f'["{collection_props.name}_display_name"]'
                if unique_display_name_prop not in bone_collection:
                    bone_collection[
                        unique_display_name_prop
                    ] = True  # Default value, change as needed


def update_rig_ui(armature):
    global rig_ui_should_update
    if not rig_ui_should_update or not armature or armature.type != "ARMATURE":
        return
    if armature and armature.type == "ARMATURE":
        rig_ui_should_update = False
        try:
            existing_collections = {
                collection.name: collection
                for collection in armature.data.collections.values()
            }

            # Sort collections with 'UI_include' on top, then by row (ascending) and priority (descending), then alphabetically
            sorted_collections = sorted(
                existing_collections.values(),
                key=lambda l: (
                    -l.get("UI_include", False),
                    l.get("row", 0),
                    -l.get("priority", 0),
                    l.name,
                ),
            )

            armature.data.bone_collection_properties.clear()
            for collection in sorted_collections:
                collection_props = armature.data.bone_collection_properties.add()
                collection_props.name = collection.name
                collection_props.row = collection.get("row", 0)
                collection_props.priority = collection.get("priority", 0)
        finally:
            rig_ui_should_update = True


class RIG_UI_UL_BoneCollections(bpy.types.UIList):
    """UI List to display and edit bone collection properties."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        armature = context.view_layer.objects.active
        if armature and armature.type == "ARMATURE":
            bone_collection = armature.data.collections.get(item.name)
            if bone_collection:
                row = layout.row(align=True)

                # UI_include toggle
                ui_include_icon = (
                    "HIDE_OFF"
                    if bone_collection.get("UI_include", False)
                    else "HIDE_ON"
                )
                row.prop(
                    bone_collection, '["UI_include"]', icon=ui_include_icon, text=""
                )

                # Icon selection as an operator button
                icon_name = bone_collection.get("icon_name", "BLANK1")
                icon_name = "BLANK1" if icon_name == "NONE" else icon_name

                # Button to open icon selector
                icon_selector_op = row.operator(
                    "rig_ui.icon_selector", text="", icon=icon_name
                )
                icon_selector_op.bone_collection_name = item.name

                # Rest of the row for name, row, and priority
                split = row.split(factor=0.5, align=True)
                split.prop(
                    bone_collection, '["display_name"]', text=item.name, toggle=True
                )
                sub_row = split.row(align=True)
                sub_row.prop(bone_collection, '["row"]', text="")
                sub_row.prop(bone_collection, '["priority"]', text="")


class RIG_UI_OT_RefreshList(bpy.types.Operator):
    """Refresh RIG UI List"""

    bl_idname = "rig_ui.refresh_list"
    bl_label = "Refresh RIG UI List"

    def execute(self, context):
        armature = context.view_layer.objects.active
        if armature and armature.type == "ARMATURE":
            update_rig_ui(armature)
        return {"FINISHED"}


class RIG_UI_PT_BoneCollectionsSetup(bpy.types.Panel):
    """Panel for managing RIG UI."""

    bl_label = "RIG UI Setup"
    bl_idname = "RIG_UI_PT_BoneCollectionsSetup"
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
            row.prop(scene, "rig_ui_edit_mode", toggle=True)
            if scene.rig_ui_edit_mode:
                # Export button next to the refresh button
                row.operator("rig_ui.refresh_list", text="", icon="FILE_REFRESH")
                row.operator("rig_ui.export_rig_ui", text="", icon="EXPORT")

            if scene.rig_ui_edit_mode:
                # Draw bone collection list first
                draw_bone_collection_list(self, context)

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
            ui_include_collections = any(
                collection.get("UI_include", False)
                for collection in armature.data.collections.values()
            )
            if ui_include_collections:
                draw_bone_collection_buttons(self, context)
            else:
                layout.label(text="Add RIG UI")
        else:
            layout.label(text="No Armature Selected.")


def draw_bone_collection_list(self, context):
    """Draws the bone collection property list in the panel."""
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
            "RIG_UI_UL_BoneCollections",
            "rig_ui",
            armature.data,
            "bone_collection_properties",
            armature.data,
            "active_bone_collection_index",
        )


def draw_bone_collection_buttons(self, context):
    """Draws buttons for RIG UI in normal mode."""
    layout = self.layout
    armature = context.view_layer.objects.active

    if armature and armature.type == "ARMATURE":
        ui_include_collections = [
            collection
            for collection in armature.data.collections.values()
            if collection.get("UI_include", False)
        ]

        sorted_ui_include_collections = sorted(
            ui_include_collections,
            key=lambda l: (l.get("row", 0), -l.get("priority", 0), l.name),
        )

        box = layout.box()
        collections_by_row = {}

        for collection in sorted_ui_include_collections:
            row_num = collection.get("row", 0)
            collections_by_row.setdefault(row_num, []).append(collection)

        for row_num in sorted(collections_by_row.keys()):
            row_layout = box.row()
            for collection in sorted(
                collections_by_row[row_num],
                key=lambda l: (-l.get("priority", 0), l.name),
            ):
                # Set icon to NONE if it is BLANK1
                icon_name = collection.get("icon_name", "NONE")
                icon_name = "NONE" if icon_name == "BLANK1" else icon_name

                display_text = (
                    collection.name if collection.get("display_name", False) else ""
                )
                row_layout.prop(
                    collection,
                    "is_visible",
                    text=display_text,
                    icon=icon_name,
                    toggle=True,
                )


def update_edit_mode(self, context):
    update_bone_collection_list(self, context)


class RIG_UI_PT_BoneCollections(bpy.types.Panel):
    """Panel for displaying RIG UI."""

    bl_label = "RIG UI"
    bl_idname = "RIG_UI_PT_BoneCollections"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        armature = context.view_layer.objects.active

        if armature and armature.type == "ARMATURE":
            # Check if any collections have 'UI_include' set to True
            ui_include_collections = any(
                collection.get("UI_include", False)
                for collection in armature.data.collections.values()
            )

            if ui_include_collections:
                draw_bone_collection_buttons(self, context)
            else:
                layout.label(text="Add RIG UI")
        else:
            layout.label(text="No Armature Selected.")


# Functions to register/unregister panels with dynamic Side Panel names
def register_panels(setup_sidepanel_name, rig_ui_sidepanel_name):
    RIG_UI_PT_BoneCollectionsSetup.bl_category = setup_sidepanel_name
    RIG_UI_PT_BoneCollections.bl_category = rig_ui_sidepanel_name
    bpy.utils.register_class(RIG_UI_PT_BoneCollectionsSetup)
    bpy.utils.register_class(RIG_UI_PT_BoneCollections)


def unregister_panels():
    if bpy.utils.unregister_class(RIG_UI_PT_BoneCollectionsSetup):
        bpy.utils.unregister_class(RIG_UI_PT_BoneCollectionsSetup)
    if bpy.utils.unregister_class(RIG_UI_PT_BoneCollections):
        bpy.utils.unregister_class(RIG_UI_PT_BoneCollections)


# Operator to update the sidepanel for the RIG UI panel
class RIG_UI_OT_UpdateSidePanel(bpy.types.Operator):
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


class RIG_UI_BoneCollectionsProperties(bpy.types.PropertyGroup):
    """Property group for bone collection properties."""

    UI_include: bpy.props.BoolProperty(name="UI Include", default=False)
    row: bpy.props.IntProperty(
        name="Row", default=1, min=1, update=update_bone_collection_list
    )
    priority: bpy.props.IntProperty(
        name="Priority", default=1, min=1, update=update_bone_collection_list
    )
    selected_icon: bpy.props.StringProperty(name="Selected Icon", default="BLANK1")
    icon_name: bpy.props.StringProperty(name="Icon Name", default="BLANK1")
    display_name: bpy.props.BoolProperty(name="Display Name", default=True)
    bpy.types.Armature.sidepanel_name = bpy.props.StringProperty(
        name="sidepanel Name",
        description="Name of the sidepanel where the RIG UI panel will be displayed",
        default="Animation",
    )


# List of classes to register
classes_to_register = [
    RIG_UI_OT_ExportToScript,
    RIG_UI_OT_UpdateSidePanelPreferences,
    BoneLayerAddonPreferences,
    RIG_UI_OT_UpdateSidePanel,
    RIG_UI_BoneCollectionsProperties,
    RIG_UI_UL_BoneCollections,
    RIG_UI_OT_RefreshList,
    RIG_UI_OT_IconSelector,
    RIG_UI_OT_ApplyIcon
    # RIG_UI_OT_SetIcon,
]

# Properties to register
properties_to_register = {
    bpy.types.Armature: [
        (
            "bone_collection_properties",
            bpy.props.CollectionProperty(type=RIG_UI_BoneCollectionsProperties),
        ),
        (
            "active_bone_collection_index",
            bpy.props.IntProperty(name="Active Bone Layer Index"),
        ),
    ],
    bpy.types.Scene: [
        (
            "rig_ui_edit_mode",
            bpy.props.BoolProperty(
                name="Edit Mode", default=True, update=update_edit_mode
            ),
        ),
        (
            "selected_bone_collection_name",
            bpy.props.StringProperty(),
        ),
        (
            "recent_icons",
            bpy.props.StringProperty(
                name="Recent Icons",
                description="List of recently selected icons",
                get=get_recent_icons,
                set=set_recent_icons,
                default="",
            ),
        ),
    ],
}


def register():
    # Register all classes
    for cls in classes_to_register:
        bpy.utils.register_class(cls)

    # Register all properties
    for prop_type, props in properties_to_register.items():
        for prop_name, prop_value in props:
            setattr(prop_type, prop_name, prop_value)

    # Additional setup if needed
    prefs = bpy.context.preferences.addons[__name__].preferences
    register_panels(prefs.rig_ui_setup_sidepanel, prefs.rig_ui_sidepanel)


def unregister():
    # Unregister all classes
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)

    # Unregister all properties
    for prop_type, props in properties_to_register.items():
        for prop_name, _ in props:
            delattr(prop_type, prop_name)

    global rig_ui_popup_instance
    global rig_ui_should_update
    rig_ui_popup_instance = None
    # Additional cleanup if needed
    unregister_panels()


if __name__ == "__main__":
    register()
