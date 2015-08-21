import bpy
import tempfile
import base64
import requests

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

def captGL(outputPath):
    '''Capture opengl in blender viewport and save the render'''
    # save current render outputPath
    temp = bpy.context.scene.render.filepath
    # Update output
    bpy.context.scene.render.filepath = outputPath
    # render opengl and write the render
    bpy.ops.render.opengl(write_still=True)
    # restore previous output path
    bpy.context.scene.render.filepath = temp

def poseLib(action=None, data=None):
    
    if action == "SNAPSHOT":
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        path = f.name + ".png"
        captGL(path)
        print(path)
        with open(path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        print(len(encoded_image))
        url = 'http://localhost:2048/edit/%s' % data
        response = requests.post(url, files={'file':encoded_image})
        
    elif action == "START_SERVER":
        start_server("localhost", 8137)
    elif action == "STOP_SERVER":
        stop_server()
        
class LFSPoseLib(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "lfs.pose_lib"
    bl_label = "LFS : Pose lib"
    
    action = bpy.props.StringProperty()
    data = bpy.props.StringProperty()

    # @classmethod
    # def poll(cls, context):
    #     return context.active_object is not None

    def execute(self, context):
        poseLib(self.action, self.data)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(LFSPoseLib)


def unregister():
    bpy.utils.unregister_class(LFSPoseLib)


if __name__ == "__main__":
    register()

# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT")

