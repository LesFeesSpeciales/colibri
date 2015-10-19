import bpy
import tempfile
import base64
import requests
import json
from mathutils import Matrix
#  * this should be in another file

def export_transforms():
    bpy.ops.object.mode_set(mode='POSE')
    boneTransform_dict = {}
    bone_list = []
    if len(bpy.context.selected_pose_bones):
        bone_list = bpy.context.selected_pose_bones
    else : 
        for arma in [r for r in bpy.data.objects if r.type == 'ARMATURE']:
            bone_list.extend(arma.pose.bones)
    
    boneTransform_dict = {}
    for bone in bone_list:
        if bone.id_data.name not in boneTransform_dict:
            boneTransform_dict[bone.id_data.name] = {}
        print('----------------')
        matrix_final = bone.matrix_basis
        matrix_json = [tuple(e) for e in list(matrix_final)]
        
        boneTransform_dict[bone.id_data.name][bone.name] = matrix_json
    return boneTransform_dict


def import_transforms(json_data, flipped=False):
    bpy.ops.object.mode_set(mode='POSE')
    json_data = json.loads(json_data.decode())
    print(json_data)
    bones = bpy.context.selected_pose_bones
    if bones == [] : 
        for rig in [r for r in bpy.data.objects if r.type == 'ARMATURE']:
            for bone in rig.pose.bones:
                bones.append(bone)

    for bone in bones:
        arma = bone.id_data.name
        if json_data.get(arma) and json_data.get(arma).get(bone.name): # If the armature is in json_data and the bone is in armature
            json_matrix = json_data.get(arma).get(bone.name) #Transforms dictionary
            #print(bone.name, ' --- ', value)
            
            matrix_final = Matrix(json_matrix)
            print(bone.name, '\n', matrix_final)
            
#            bone.matrix_world = matrix_final
            bone.matrix_basis = matrix_final
###


def select_bones(json_data):
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    json_data = json.loads(json_data.decode())
    print(json_data)
    bones = []
    if bones == [] : 
        for rig in [r for r in bpy.data.objects if r.type == 'ARMATURE']:
            for bone in rig.pose.bones:
                bones.append(bone)
    for bone in bones:
        arma = bone.id_data.name
        if json_data.get(arma) and json_data.get(arma).get(bone.name):
            print(bone)
            bone.bone.select = True

def captGL(outputPath):
    '''Capture opengl in blender viewport and save the render'''
    # save current render outputPath

    values = {
            'bpy.context.scene.render.filepath': "toto", #outputPath,
            'bpy.context.scene.render.resolution_x': 600,
            'bpy.context.scene.render.resolution_y': 600,
            'bpy.context.scene.render.resolution_percentage': 100,
            'bpy.context.scene.render.image_settings.file_format': 'PNG',
            'bpy.context.scene.render.image_settings.color_mode': 'RGBA',
            # 'bpy.context.space_data.show_only_render': True, A definir
        }
    values_temp = {}
    for v in values:
        values_temp[v] = eval(v)
        exec("%s = %s" % (v, '"%s"' % values[v] if type(values[v]) == str else str(values[v])))


    # Update output
    bpy.context.scene.render.filepath = outputPath
    print("captGL outputPath :")
    print(bpy.context.scene.render.filepath)
    # render opengl and write the render
    bpy.ops.render.opengl(write_still=True)
    # restore previous output path
    for v in values_temp:
        exec("%s = %s" % (v, '"%s"' % values_temp[v] if type(values_temp[v]) == str else str(values_temp[v])))

class LFSColibriApplyPose(bpy.types.Operator):
    ''''''

    bl_idname = "lfs.colibri_apply_pose"
    bl_label = "LFS : Apply pose"

    jsonPose = bpy.props.StringProperty()
    flipped = bpy.props.BoolProperty(default=False)

    def execute(self, context):
        import_transforms(base64.b64decode(self.jsonPose), self.flipped)
        return {'FINISHED'}



# def poseLib(action=None, data=None, jsonPose=None):
#     print(action)
#     print(data)
#     print(jsonPose)
#     source_file = bpy.data.filepath
#     if action == "SNAPSHOT":
#         f = tempfile.NamedTemporaryFile(delete=False)
#         f.close()
#         path = f.name + ".png"
#         captGL(path)
#         print(path)
#         with open(path, "rb") as image_file:
#             encoded_image = base64.b64encode(image_file.read())
#         print(len(encoded_image))
#         url = 'http://%s:2048/pose/%s' % (hostname, data)
#         response = requests.post(url, params={'field': 'thumbnail', 'source_file':source_file}, files={'file':encoded_image})
#     elif action == "SELECT_BONES":
#         select_bones(base64.b64decode(jsonPose))
    
#     elif action == "EXPORT_POSE":
#         p = json.dumps(export_transforms())
#         url = 'http://%s:2048/pose/%s' % (hostname,data)
#         response = requests.post(url, params={'field':'json_fromBlender', 'json':p, 'source_file':source_file})
#     elif action == "APPLY_POSE":
#         import_transforms(base64.b64decode(jsonPose))


def register():
    bpy.utils.register_class(LFSColibriApplyPose)


def unregister():
    bpy.utils.unregister_class(LFSColibriApplyPose)


if __name__ == "__main__":
    register()