import bpy
from bpy.app.handlers import persistent
from bpy.ops import op_as_string
import json
import uuid

import queue
import threading

# Specify here you lib path for ws4py if not properly done
import sys
sys.path.append('/u/lib/')

from wsgiref.simple_server import make_server
from ws4py.websocket import WebSocket as _WebSocket
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication


# commands are allowed to run from that list
# Default is localhost only
white_list = ['127.0.0.1']

# If False, any connection out of white_list refused.
# If True : prompted to accept (not yet)
OPEN_SOCKET = False

port = 8137      # Server default port
port_range = 10  # number of tried ports incrementing from 'port' variable


# need to store different stuff. Do not change :
wserver = None
wserver_thread = None
message_queue = queue.Queue()
sockets = []
callBacks = {}


def registerCallBack(callback):
    '''register a call back function with an assigned uuid
       used to enable callbacks from operators to the socket'''

    k = str(uuid.uuid4())
    callBacks[k] = callback
    return k


class WebSocketApp(_WebSocket):
    '''This class handle the websockets opening,
       remote closing and messages reception'''

    def opened(self):
        print("New connection opened from : %s" % self.peer_address[0])
        if self.peer_address[0] not in white_list and OPEN_SOCKET is False:
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
    '''Start a webserver'''

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
    '''Stoping the webserver, closing the sockets, ...'''

    global wserver, wserver_thread
    if not wserver:
        return False

    for socket in sockets:
        socket.close(code=1001)
    wserver.shutdown()
    wserver_thread._stop()  # not documented but working well

    bpy.app.handlers.scene_update_post.remove(scene_update)
    wserver = None
    return True


@persistent
def scene_update(context):
    '''This is checking the message queue list'''

    while not message_queue.empty():
        message, socket = message_queue.get()
        callback_idx = registerCallBack(lambda msgToSend: socket.send(msgToSend))
        bpy.ops.lfs.message_dispatcher(message=message, callback_idx=callback_idx)


def operator_exists(idname):
    '''simple function that returns if an operator exists'''

    try:
        op_as_string(idname)
        return True
    except:
        return False


class LFSBlenderPing(bpy.types.Operator):
    """Simple demo operator that returns current openned file"""

    bl_idname = "lfs.blender_ping"
    bl_label = "LFS : Bleder Ping"

    callback_idx = bpy.props.StringProperty()

    def execute(self, context):
        msgBack = {'port': port, 'operator': 'lfs.blender_ping', 'file': bpy.data.filepath}
        bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message=json.dumps(msgBack))
        return {'FINISHED'}


class LFSMessageCallBack(bpy.types.Operator):
    """Used to send messages back to the used socket"""

    bl_idname = "lfs.message_callback"
    bl_label = "LFS : Message Call Back"

    callback_idx = bpy.props.StringProperty()
    message = bpy.props.StringProperty()

    def execute(self, context):
        print("Message Call Back to %s : %s" % (self.callback_idx, self.message))
        callBacks[self.callback_idx](self.message)
        del callBacks[self.callback_idx]  # Callback can only be used once
        return {'FINISHED'}


class LFSMessageDispatcher(bpy.types.Operator):
    '''The main operator that get the messages and check them before exec'''

    bl_idname = "lfs.message_dispatcher"
    bl_label = "LFS : Message Dispatcher"

    message = bpy.props.StringProperty()
    callback_idx = bpy.props.StringProperty()

    # message should be a json string
    # Contains a least an operator parameter to call

    def execute(self, context):
        # poseLib(self.action, self.data, self.jsonPose)
        print("Message dispatcher executed :")
        print(self.message)
        print(self.callback_idx)

        try:
            # msg SHOULD be a valid json string
            msg = json.loads(self.message)
        except:
            self.report({'ERROR'}, "message is no valid json")
            bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message="ERROR : message no json")
            return {'CANCELLED'}

        if 'operator' not in msg:
            # msg lib should have an operator key
            self.report({'ERROR'}, "Json not well formated : no operator specified in json ")
            bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message="ERROR : no operator specified in json ")
            return {'CANCELLED'}

        if operator_exists(msg['operator']) is False:
            # the operator to call need to be register before
            # You cant run function not registered
            self.report({'ERROR'}, "Operator %s not defined" % msg['operator'])
            bpy.ops.lfs.message_callback(callback_idx=self.callback_idx, message="ERROR, Operator %s not defined" % msg['operator'])
            return {'CANCELLED'}

        # getting the function you're looking for
        ns = getattr(bpy.ops, msg['operator'].split('.')[0])
        f = getattr(ns, msg['operator'].split('.')[1])

        # preparing the callback id if needed by the operator to call
        if 'callback_idx' in dir(f.get_rna()):
            msg['callback_idx'] = self.callback_idx
            # Attention, not having a parameter callback_idx in your operator
            # Will provide any easy callback to the socket

        # removing 'operator' key if not used by the operator to be called
        if 'operator' not in dir(f.get_rna()):
            msg.pop("operator", None)
        # all other keys sent by the app are up to you !

        # calling the operator, providing the message
        f(**msg)

        return {'FINISHED'}


class LFSStartServer(bpy.types.Operator):
    """Operator to start a server"""

    bl_idname = "lfs.start_server"
    bl_label = "LFS : Start Server"

    port = bpy.props.IntProperty()
    host = bpy.props.StringProperty()

    def execute(self, context):
        start_server(self.host, self.port)
        return {'FINISHED'}


class LFSStopServer(bpy.types.Operator):
    """Operator to stop the server"""

    bl_idname = "lfs.stop_server"
    bl_label = "LFS : Stop Server"

    def execute(self, context):
        stop_server()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(LFSMessageDispatcher)
    bpy.utils.register_class(LFSMessageCallBack)
    bpy.utils.register_class(LFSBlenderPing)
    bpy.utils.register_class(LFSStartServer)
    bpy.utils.register_class(LFSStopServer)


def unregister():
    bpy.utils.unregister_class(LFSMessageDispatcher)
    bpy.utils.unregister_class(LFSMessageCallBack)
    bpy.utils.unregister_class(LFSBlenderPing)
    bpy.utils.unregister_class(LFSStartServer)
    bpy.utils.unregister_class(LFSStopServer)

if __name__ == "__main__":
    register()


# bpy.ops.lfs.start_server("EXEC_DEFAULT", host="localhost", port=8137)
# bpy.ops.lfs.stop_server("EXEC_DEFAULT")
