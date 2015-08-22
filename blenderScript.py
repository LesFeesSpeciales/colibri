import bpy
import tempfile
import base64
import requests
import json
from mathutils import Matrix

import sys
sys.path.append('/u/lib/')

### SERVER


from wsgiref.simple_server import make_server
from ws4py.websocket import WebSocket as _WebSocket
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication

import queue
import threading
import bpy
from bpy.app.handlers import persistent


hostname = "localhost"
wserver = None
message_queue = queue.Queue()
sockets = []


class WebSocketApp(_WebSocket):
    def opened(self):
        sockets.append(self)
        
    def closed(self, code, reason=None):
        sockets.remove(self)
        
    def received_message(self, message):
        # exec(str(message))
        message_queue.put(message.data.decode(message.encoding))


def start_server(host, port):
    global wserver
    if wserver:
        return False
    
    wserver = make_server(host, port,
        server_class=WSGIServer,
        handler_class=WebSocketWSGIRequestHandler,
        app=WebSocketWSGIApplication(handler_cls=WebSocketApp)
    )
    wserver.initialize_websockets_manager()
    
    wserver_thread = threading.Thread(target=wserver.serve_forever)
    wserver_thread.daemon = True
    wserver_thread.start()

    bpy.app.handlers.scene_update_post.append(scene_update)
        
    return True


def stop_server():
    global wserver
    if not wserver:
        return False
        
    wserver.shutdown()
    for socket in sockets:
        socket.close()
        
    wserver = None
    
    bpy.app.handlers.scene_update_post.remove(scene_update)
    
    return True

    
@persistent 
def scene_update(context):
    while not message_queue.empty():
        data = message_queue.get()
        print(data)
        exec (data)
    
    
# def scene_update(context):
    # if bpy.data.objects.is_updated:
        # print("One or more objects were updated!")
        # for ob in bpy.data.objects:
            # if ob.is_updated:
                # print("=>", ob.name)

### start_server("localhost", 8137)


### 
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

def import_transforms(json_data):
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


def captGL(outputPath):
    '''Capture opengl in blender viewport and save the render'''
    # save current render outputPath
    temp = bpy.context.scene.render.filepath
    # Update output
    bpy.context.scene.render.filepath = outputPath
    print("captGL outputPath :")
    print(bpy.context.scene.render.filepath)
    # render opengl and write the render
    bpy.ops.render.opengl(write_still=True)
    # restore previous output path
    bpy.context.scene.render.filepath = temp

def poseLib(action=None, data=None, jsonPose=None):
    print(action)
    print(data)
    print(jsonPose)
    if action == "SNAPSHOT":
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        path = f.name + ".png"
        captGL(path)
        print(path)
        with open(path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        print(len(encoded_image))
        url = 'http://%s:2048/edit/%s' % (hostname, data)
        response = requests.post(url, files={'file':encoded_image})
        
    elif action == "START_SERVER":
        start_server("localhost", 8137)
    elif action == "STOP_SERVER":
        stop_server()
    elif action == "EXPORT_POSE":
        p = json.dumps(export_transforms())
        url = 'http://%s:2048/edit/%s' % (hostname,data)
        response = requests.post(url, params={'blenderPose':p})
    elif action == "APPLY_POSE":
        print(base64.b64decode(jsonPose))
        import_transforms(base64.b64decode(jsonPose))
        
class LFSPoseLib(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "lfs.pose_lib"
    bl_label = "LFS : Pose lib"
    
    action = bpy.props.StringProperty()
    data = bpy.props.StringProperty()
    jsonPose = bpy.props.StringProperty()

    # @classmethod
    # def poll(cls, context):
    #     return context.active_object is not None

    def execute(self, context):
        poseLib(self.action, self.data, self.jsonPose)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(LFSPoseLib)


def unregister():
    bpy.utils.unregister_class(LFSPoseLib)


if __name__ == "__main__":
    register()

# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT")

