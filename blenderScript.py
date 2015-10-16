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

hostname = "localhost"  # server target to send back data # 
white_list = ['127.0.0.1']  # commands are allowed to run from that list
OPEN_SOCKET = True
current_socket = None
port = 8137
port_range = 10  # number of tried ports (incrementing from 'port' variable) before failing

# Change if you server is centralized and not on the same host
wserver = None
wserver_thread = None
message_queue = queue.Queue()
sockets = []


# If false, you will not get any message from distant connections (still printed)
# If True the message will still be put on the queue list, 
# but still checked before exec
# If message is coming from anything else than the white_list
# Blender will open a pop_up to ask if you want to allow that source to exec code

class WebSocketApp(_WebSocket):
    def opened(self):
        if self.peer_address[0] not in white_list and OPEN_SOCKET == False:
            print("Incoming connection from %s refused" % self.peer_address[0])
            return
        else:
            sockets.append(self)
        
    def closed(self, code, reason=None):
        sockets.remove(self)
        
    def received_message(self, message):
        print(self.peer_address)
        print(message)
        if self not in sockets:
            print("Incoming message from %s refused : %s" % (self.peer_address[0], message))
        else:
            message_queue.put((message.data.decode(message.encoding), self)) # (the_message, socket)


def start_server(host, port):
    global wserver, wserver_thread
    if wserver:
        print("Server already running ?")
        return False
    
    
    source_port = port
    while not wserver or source_port + port_range <= port:
        print("Starting server on port %i" % port)
        try:
            
            wserver = make_server(host, port,
                server_class=WSGIServer,
                handler_class=WebSocketWSGIRequestHandler,
                app=WebSocketWSGIApplication(handler_cls=WebSocketApp)
            )
            wserver.initialize_websockets_manager()
        except:
            print("Unable to start the server on port %i"% port)
            port += 1
            if source_port + port_range <= port:
                print("Tried all ports without finding one available")
                return
    
    wserver_thread = threading.Thread(target=wserver.serve_forever)
    wserver_thread.daemon = True
    wserver_thread.start()    
    return True

def stop_server():
    global wserver
    if not wserver:
        return False
        
    wserver.shutdown()
    wserver_thread.stop()
    for socket in sockets:
        socket.close()
        

    
    #bpy.app.handlers.scene_update_post.remove(scene_update)
    
    return True

    
@persistent 
def scene_update(context):
    while not message_queue.empty():
        global current_socket
        data, current_socket = message_queue.get()
        print(data)
        if socket.peer_address[0] not in white_list:
            # You should ask the user first
            # Save it for later, open popup and prompt for allowing the peer_address
            pass
        else:
            exec(data)


# ##
# ##     NOW LET'S TALK POSE LIBRARY FUNCTIONS *
# ##

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



def poseLib(action=None, data=None, jsonPose=None):
    print(action)
    print(data)
    print(jsonPose)
    source_file = bpy.data.filepath
    if action == "SNAPSHOT":
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        path = f.name + ".png"
        captGL(path)
        print(path)
        with open(path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        print(len(encoded_image))
        url = 'http://%s:2048/pose/%s' % (hostname, data)
        response = requests.post(url, params={'field': 'thumbnail', 'source_file':source_file}, files={'file':encoded_image})
    elif action == "SELECT_BONES":
        select_bones(base64.b64decode(jsonPose))
    elif action == "START_SERVER":
        start_server("localhost", port)
    elif action == "STOP_SERVER":
        stop_server()
    elif action == "EXPORT_POSE":
        p = json.dumps(export_transforms())
        url = 'http://%s:2048/pose/%s' % (hostname,data)
        response = requests.post(url, params={'field':'json_fromBlender', 'json':p, 'source_file':source_file})
    elif action == "APPLY_POSE":
        import_transforms(base64.b64decode(jsonPose))
    elif action == "BLENDER_PING":
        if current_socket:
            current_socket.send("source_file:%s" % (source_file))
        
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

# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT", data="10"})
# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="EXPORT_POSE", data="10")
# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="START_SERVER")
