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
        # print('----------------')
        matrix_final = bone.matrix_basis
        matrix_json = [tuple(e) for e in list(matrix_final)]
        
        boneTransform_dict[bone.id_data.name][bone.name] = matrix_json
    return boneTransform_dict


def import_transforms(target_pose_data, initial_pose_data=None, merge_factor=None, flipped=False):
    # ATTENTION : appeler cette fonction avec flipped=True pour appliquer sur l'autre partie du rig.
    # ça utilise le copier-coller de poses de blender
    # je n'ai pas implemente la communication avec l'interface web.
    bpy.ops.object.mode_set(mode='POSE')
    target_pose_data = json.loads(target_pose_data.decode())
    if initial_pose_data is not None:
        initial_pose_data = json.loads(initial_pose_data.decode())
        merge_factor = float(merge_factor) # convert to [0,1] value
        # print("MERGE FACTOR", merge_factor)
        merge_factor /= 100 # convert to [0,1] value
        # print("MERGE FACTOR", merge_factor)
        # print("type", type(merge_factor))
    # print(target_pose_data)
    bones = bpy.context.selected_pose_bones
    if bones == [] : 
        for rig in [r for r in bpy.data.objects if r.type == 'ARMATURE']:
            for bone in rig.pose.bones:
                bones.append(bone)
        
    if flipped:
        tmp_bones = {}
    for bone in bones:
        arma = bone.id_data.name
        if target_pose_data.get(arma) and target_pose_data.get(arma).get(bone.name): # If the armature is in target_pose_data and the bone is in armature
            json_matrix = Matrix(target_pose_data.get(arma).get(bone.name)) #Transforms dictionary

            if initial_pose_data is not None:# and bone.name in initial_pose_data.get(arma):
                json_matrix = Matrix(target_pose_data.get(arma).get(bone.name))

                json_matrix *= merge_factor
                json_matrix += Matrix(initial_pose_data.get(arma).get(bone.name)) * (1.0 - merge_factor)
            #print(bone.name, ' --- ', value)
            matrix_final = Matrix(json_matrix)
            #print(bone.name, '\n', matrix_final)
            
#            bone.matrix_world = matrix_final
            if flipped:
                tmp_bones[bone.name] = bone.matrix_basis.copy()
                bone.bone.select = True
            bone.matrix_basis = matrix_final
    
    # print("MERGE FACTOR", merge_factor)

    if flipped:
        bpy.ops.pose.copy()
        for bone, mat in tmp_bones.items():
            bpy.context.object.pose.bones[bone].matrix_basis = mat
        bpy.ops.pose.paste(flipped=True)
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


class LFSColibriApplyPose(bpy.types.Operator):
    '''Get a pose a a base64 encoded json and apply it
    '''

    bl_idname = "lfs.colibri_apply_pose"
    bl_label = "LFS : Apply pose"


    jsonPose = bpy.props.StringProperty()
    flipped = bpy.props.BoolProperty(default=False)
    select_only = bpy.props.BoolProperty(default=False)
    # for merging poses
    initial_pose = bpy.props.StringProperty(default="")
    merge_factor = bpy.props.IntProperty(default=-1)

    callback_idx = bpy.props.StringProperty()

    def execute(self, context):
        print(self.select_only)
        if self.select_only:
            select_bones(base64.b64decode(self.jsonPose))
        elif not self.initial_pose:
            import_transforms(base64.b64decode(self.jsonPose), flipped=self.flipped)
        else:
            # Merging pose
            # DAMIEN
            target_pose = base64.b64decode(self.jsonPose)
            initial_pose = base64.b64decode(self.initial_pose)
            merge_factor = self.merge_factor
            import_transforms(target_pose, initial_pose_data=initial_pose, merge_factor=merge_factor, flipped=self.flipped)

            # print("Merging poses by a factor of %i percents" % merge_factor)
            # print("Initial pose: ", initial_pose)
            # print("Target pose: ", target_pose)
        msgBack = {'operator': 'lfs.colibri_apply_pose'}
        bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message=json.dumps(msgBack))
        return {'FINISHED'}

class LFSColibriMakeSnatpshot(bpy.types.Operator):
    '''Make a snapshot (openGlRender) and send it to the server'''

    bl_idname = "lfs.colibri_snapshot"
    bl_label = "LFS : Make a snapshot"

    hostname = bpy.props.StringProperty(default="localhost")
    pose_id = bpy.props.StringProperty()
    callback_idx = bpy.props.StringProperty()

    def execute(self, context):
        # creating a temp file
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        path = f.name + ".png"
        
        # Setting the render values
        values = {
            'bpy.context.scene.render.filepath': path,
            'bpy.context.scene.render.resolution_x': 600,
            'bpy.context.scene.render.resolution_y': 600,
            'bpy.context.scene.render.resolution_percentage': 100,
            'bpy.context.scene.render.image_settings.file_format': 'PNG',
            'bpy.context.scene.render.image_settings.color_mode': 'RGBA',
            # 'bpy.context.space_data.show_only_render': True, A definir
            }
        values_temp = {}
        # Saving the previous values and applying the thumbnail ones
        for v in values:
            values_temp[v] = eval(v)
            exec("%s = %s" % (v, '"%s"' % values[v] if type(values[v]) == str else str(values[v])))

        # Update output
        #bpy.context.scene.render.filepath = outputPath
        print("captGL outputPath :")
        print(bpy.context.scene.render.filepath)
        # render opengl and write the render
        bpy.ops.render.opengl(write_still=True)
        # restore previous output path
        for v in values_temp:
            exec("%s = %s" % (v, '"%s"' % values_temp[v] if type(values_temp[v]) == str else str(values_temp[v])))

        # Open the rendered image and encode it as base64

        with open(path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        print(len(encoded_image))
        # Sending the image to the server
        url = 'http://%s:2048/pose/%s' % (self.hostname, self.pose_id)
        response = requests.post(url, params={'field': 'thumbnail', 'source_file':bpy.data.filepath}, files={'file':encoded_image})
    
        # Callback to warn the image is uploaded
        msgBack = {'operator': 'lfs.colibri_snapshot', 'pose_id': self.pose_id, 'filepath': bpy.data.filepath}
        bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message=json.dumps(msgBack))
        
        return {'FINISHED'}

class LFSColibriGetPose(bpy.types.Operator):
    '''Get a pose a a base64 encoded json and apply it
    '''

    bl_idname = "lfs.colibri_get_pose"
    bl_label = "LFS : Get pose"

    to = bpy.props.StringProperty(default="normal")
    callback_idx = bpy.props.StringProperty()
    pose_id = bpy.props.StringProperty(default="")

    def execute(self, context):
        p = json.dumps(export_transforms())
        msgBack = {'poseB64': base64.b64encode(p.encode('ascii')).decode(),
                   'operator': 'lfs.colibri_get_pose',
                   'to': self.to,
                   'pose_id': self.pose_id,
                   'source_file':bpy.data.filepath}
        bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message=json.dumps(msgBack))
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
    bpy.utils.register_class(LFSColibriMakeSnatpshot)
    bpy.utils.register_class(LFSColibriGetPose)

def unregister():
    bpy.utils.unregister_class(LFSColibriApplyPose)
    bpy.utils.unregister_class(LFSColibriMakeSnatpshot)
    bpy.utils.unregister_class(LFSColibriGetPose)

if __name__ == "__main__":
    register()