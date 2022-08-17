from pathlib import Path
from math import radians

OVERWRITE = False
TEST_FIRST = False

def main():
    target_dir = Path()

    thumbnails = []

    context = bpy.context
    for file in target_dir.rglob("*"):
        if file.suffix.lower() == ".wrz":
            thumbnail_path = (file.parent / (file.stem + ".webp"))
            thumbnails.append(thumbnail_path)

            if OVERWRITE or not thumbnail_path.is_file():
                generate_thumbnail(file, context)
                if TEST_FIRST:
                    return
                bpy.ops.wm.read_homefile()

            with open(file.parent / "README.md", "w") as readme:
                readme.write(f"![{file.stem}]({thumbnail_path.name})\n")

    tile_size = 500
    n_columns = 9
    n_rows = (len(thumbnails) - 1) // n_columns + 1

    x_size = n_columns * tile_size
    y_size = n_rows * tile_size
    overview_image = bpy.data.images.new("overview", x_size, y_size)
    overview_array = np.full((y_size, x_size * 4), np.tile((0.1, 0.1, 0.1, 1.0), x_size))
    
    for i, thumbnail_path in enumerate(thumbnails):
        thumbnail_image = bpy.data.images.load(str(thumbnail_path.resolve()))
        thumbnail_image.scale(tile_size, tile_size)
        column = i % n_columns
        row = n_rows - i // n_columns - 1
        
        x_start = column * tile_size * 4
        x_end = x_start + tile_size * 4
        y_start = row * tile_size
        y_end = y_start + tile_size
        pixels = np.reshape(thumbnail_image.pixels[:], (tile_size, tile_size * 4))
        overview_array[y_start:y_end,x_start:x_end] = pixels

    overview_image.pixels = overview_array.flatten()

    render = context.scene.render
    render.image_settings.file_format = "WEBP"
    render.image_settings.color_mode = "RGB"
    render.image_settings.quality = 95
    overview_image.save_render(str(target_dir.resolve() / "overview.webp"))

def generate_thumbnail(target_file: Path, context):
    if all(addon_utils.check("pcb2blender_importer")):
        bpy.ops.pcb2blender.import_x3d(filepath=str(target_file))
    else:
        bpy.ops.import_scene.x3d(filepath=str(target_file), axis_up="Z", axis_forward="-Y")
        context.view_layer.objects.active = context.view_layer.objects[0]
        bpy.ops.object.join()
        bpy.ops.object.shade_smooth()
        context.object.scale *= 1e-3

    target_obj = context.object

    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")
    target_obj.location = (0, 0, 0)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    target_obj.location.z = 0

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    size = 2 * max((abs(target_obj.bound_box[i][j]) for i in range(8) for j in range(3)))
    size_stepped = max(round(size * 50), 1) / 50

    bpy.ops.object.camera_add()
    camera_obj = context.object
    rotation = Euler((radians(55), 0, radians(25)))
    camera_obj.rotation_euler = rotation
    camera_obj.location = rotation.to_quaternion() @ Vector((0, 0, size_stepped * 13))
    camera = camera_obj.data
    camera.clip_start = 0.01
    camera.lens = 250

    if all(addon_utils.check("Gaffer")):
        from Gaffer.functions import hdri_enum_previews
        gaffer = context.scene.gaf_props
        gaffer.hdri_handler_enabled = True
        hdri = "photo_studio_loft_hall"
        if hdri in (enum[0] for enum in hdri_enum_previews(None, context)):
            gaffer.hdri = hdri
        else:
            print(f"failed to find {hdri} hdri")
        gaffer.hdri_saturation = 0.4
        gaffer.hdri_warmth = 1.4
        gaffer.hdri_rotation = 35
        gaffer.hdri_use_separate_brightness = True
        gaffer.hdri_background_brightness = -5.5
        gaffer.hdri_use_separate_contrast = True
        gaffer.hdri_background_contrast = 0
        context.view_layer.update()

    context.scene.camera = camera_obj
    render = context.scene.render
    render.filepath = str(target_file.parent.absolute() / target_file.stem)
    render.image_settings.file_format = "WEBP"
    render.image_settings.color_mode = "RGB"
    render.image_settings.quality = 95
    render.resolution_x = 1000
    render.resolution_y = 1000

    render.use_stamp = True
    render.use_stamp_note = True
    render.stamp_note_text = f" {target_file.stem} "
    render.stamp_font_size = 24
    for attr in dir(render):
        if attr.startswith("use_stamp_") and not attr == "use_stamp_note":
            setattr(render, attr, False)

    render.engine = "CYCLES"
    cycles = context.scene.cycles
    cycles.samples = 32
    cycles.use_denoising = True

    bpy.ops.render.render(write_still=True)

if __name__ == "__main__":
    try:
        import bpy
        from mathutils import Vector, Euler
        import addon_utils
        import numpy as np

        if not bpy.app.version:
            raise ModuleNotFoundError()

    except ModuleNotFoundError:
        print("blender -b -P generate-thumbnails.py")
        exit()

    main()
