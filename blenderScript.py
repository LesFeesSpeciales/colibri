import bpy
from bpy.app.handlers import persistent

# import tempfile
# import base64
# import requests
import json
# from mathutils import Matrix

import uuid

import sys
sys.path.append('/u/lib/')

from wsgiref.simple_server import make_server
from ws4py.websocket import WebSocket as _WebSocket
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication

import queue
import threading

hostname = "localhost"  # server target to send back data #
white_list = ['127.0.0.1']  # commands are allowed to run from that list
OPEN_SOCKET = False  # If False, any connection out of white_list refused. If True : prompted to accept
port = 8137
port_range = 10  # number of tried ports (incrementing from 'port' variable) before failing

# Change if you server is centralized and not on the same host
wserver = None
wserver_thread = None
message_queue = queue.Queue()
sockets = []
callBacks = {}


def registerCallBack(callback):
    '''register a call back function with an assigned uuid'''
    k = str(uuid.uuid4())
    callBacks[k] = callback
    return k


class WebSocketApp(_WebSocket):
    def opened(self):
        print("New connection opened from : %s" % self.peer_address[0])
        if self.peer_address[0] not in white_list and OPEN_SOCKET == False:
            print("Incoming connection from %s refused" % self.peer_address[0])
            self.close(code=1008, reason="Connection not allowed")
            return

        sockets.append(self)

    def closed(self, code, reason=None):
        print('Connection from %s closed %i : %s'
              % (self.peer_adress, code, reason))
        sockets.remove(self)

    def received_message(self, message):
        print(self.peer_address)
        print(message.data.decode(message.encoding))

        message_queue.put((message.data.decode(message.encoding), self))  # (the_message, socket)


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
            print("Unable to start the server on port %i" % port)
            port += 1
            if source_port + port_range <= port:
                print("Tried all ports without finding one available")
                return

    wserver_thread = threading.Thread(target=wserver.serve_forever)
    wserver_thread.daemon = True
    wserver_thread.start()

    bpy.app.handlers.scene_update_post.append(scene_update)

    return True


def stop_server():
    global wserver
    if not wserver:
        return False

    for socket in sockets:
        socket.close(code=1001)
    wserver.shutdown()

    bpy.app.handlers.scene_update_post.remove(scene_update)

    return True


@persistent
def scene_update(context):
    #  print("Checking")
    while not message_queue.empty():
        message, socket = message_queue.get()
        print(message)
        # message should be a json format
        # {'operator':'the operator name to call',
        #  'callback_needed':True/False,
        #  anyOtherKey
        #  }
        # exec(message)
        callBack_idx = registerCallBack(lambda msgToSend: socket.send(msgToSend))
        bpy.ops.lfs.message_dispatcher(message=message, callBack_idx=callBack_idx)


def operator_exists(idname):
    from bpy.ops import op_as_string
    try:
        op_as_string(idname)
        return True
    except:
        return False


class LFSBlenderPing(bpy.types.Operator):
    """ToDo"""
    bl_idname = "lfs.blender_ping"
    bl_label = "LFS : Bleder Ping"

    callBack_idx = bpy.props.StringProperty()
    operator = bpy.props.StringProperty()

    def execute(self, context):
        msgBack = {'port': port, 'operator': self.operator, 'file':bpy.data.filepath}
        bpy.ops.lfs.message_callback(callBack_idx=self.callBack_idx, message=json.dumps(msgBack))
        return {'FINISHED'}


class LFSMessageCallBack(bpy.types.Operator):
    """Class """
    bl_idname = "lfs.message_callback"
    bl_label = "LFS : Message Call Back"

    callBack_idx = bpy.props.StringProperty()
    message = bpy.props.StringProperty()

    def execute(self, context):
        print("Message Call Back")
        print(self.callBack_idx)
        print(self.message)
        callBacks[self.callBack_idx](self.message)
        del callBacks[self.callBack_idx]
        return {'FINISHED'}


class LFSMessageDispatcher(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "lfs.message_dispatcher"
    bl_label = "LFS : Message Dispatcher"

    message = bpy.props.StringProperty()
    callBack_idx = bpy.props.StringProperty()


    # message should be a json string
    # Contains a least an operator parameter to call

    def execute(self, context):
        # poseLib(self.action, self.data, self.jsonPose)
        print("Message dispatcher executed :")
        print(self.message)
        print(self.callBack_idx)

        try:
            msg = json.loads(self.message)
        except:
            print("ERROR, message is no json")
            bpy.ops.lfs.message_callback(callBack_idx=self.callBack_idx, message="ERROR : message no json")
            return {'CANCELLED'}

        if 'operator' not in msg:
            print("ERROR, no operator specified in json ")
            bpy.ops.lfs.message_callback(callBack_idx=self.callBack_idx, message="ERROR : no operator specified in json ")
            return {'CANCELLED'}
        if operator_exists(msg['operator']) is False:
            print("ERROR, Operator %s not defined" % msg['operator'])
            bpy.ops.lfs.message_callback(callBack_idx=self.callBack_idx, message="ERROR, Operator %s not defined" % msg['operator'])
            return {'CANCELLED'}

        ns = getattr(bpy.ops, msg['operator'].split('.')[0])
        f = getattr(ns, msg['operator'].split('.')[1])

        msg['callBack_idx'] = self.callBack_idx
        f(**msg)
        #bpy.ops.lfs.message_callback(idx=self.callBack_idx, message="message back !")
        return {'FINISHED'}

# class LFSPoseLib(bpy.types.Operator):
#     """Tooltip"""
#     bl_idname = "lfs.pose_lib"
#     bl_label = "LFS : Pose lib"
    
#     action = bpy.props.StringProperty()
#     data = bpy.props.StringProperty()
#     jsonPose = bpy.props.StringProperty()

#     # @classmethod
#     # def poll(cls, context):
#     #     return context.active_object is not None

#     def execute(self, context):
#         poseLib(self.action, self.data, self.jsonPose)
#         return {'FINISHED'}


def register():
    bpy.utils.register_class(LFSMessageDispatcher)
    bpy.utils.register_class(LFSMessageCallBack)
    bpy.utils.register_class(LFSBlenderPing)


def unregister():
    bpy.utils.unregister_class(LFSMessageDispatcher)
    bpy.utils.unregister_class(LFSMessageCallBack)
    bpy.utils.unregister_class(LFSBlenderPing)

if __name__ == "__main__":
    register()

# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT", data="10"})
# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="EXPORT_POSE", data="10")
# bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="START_SERVER")

start_server("localhost", port)
