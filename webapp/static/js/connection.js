var port = 8137
var connection = new WebSocket('ws://localhost:' + port);


connectionTimeOut = setTimeout(function (){
    console.log("socket timeout");
    $('#connection_msg').html('Connection timeout on port '+port+'.')

 }, 2000);


connection.binaryType = "arraybuffer";

//{"operator": "lfs.blender_ping", "filepath": "/Users/flavioperez/Downloads/victor.blend/testConnection.blend", "filename": "testConnection.blend"}

connection.onopen = function () {
    // When the socket opens, log it and send two messages"
    console.log("socket opened");
    $('#connection_msg').html('Connected');
    clearTimeout(connectionTimeOut);
    var myO = {"operator":"lfs.blender_ping"};
    var myOStr = JSON.stringify(myO);
    connection.send(myOStr);

    //for (var i=0; i<50; i++)
    //{
    
    //connection.send('bpy.ops.mesh.primitive_monkey_add(radius=1, view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))');
    //}
//    connection.send('bytes');
};

connection.onclose = function (close) {
    console.log('WebSocket Closed ' + close);
    $('#connection_msg').html('Connection closed on port '+port+'.')
    clearTimeout(connectionTimeOut);
};

 
connection.onerror = function (error) {
    console.log('WebSocket Error ' + error);
    $('#connection_msg').html('Connection error on port '+port+'.')
    clearTimeout(connectionTimeOut);
};


connection.onmessage = function (e) {
    console.log('Message from server');
    if (e.data instanceof ArrayBuffer) {
        // If it's ArrayBuffer it must be the binary array 0x00 .. 0xff we're expecting
        var byteArray = new Uint8Array(e.data);
        if (byteArray.length != 256) {
            console.log("Error; didn't get expected length 256");
            return;
        }
        for (var i = 0; i < byteArray.length; i++) {
            if (byteArray[i] != i) {
                console.log("Error; got " + byteArray[i] + " at position " + i);
                return;
            }
        }
        console.log("Received expected 256 byte array");
    } else {
        // Print out any other message from the server
        console.log(e.data);
        var obj = JSON.parse(e.data);
        if (obj.operator == "lfs.blender_ping"){
              $('#connection_msg').html(obj.filename);
         }else{
              alert(e.data);
         }

        
    }
};


function updateSlider()
{
    connection.send('bpy.context.object.location[0] = '+document.getElementById("slide").value);

//  connection.send('bpy.ops.mesh.primitive_monkey_add(radius=1, view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))');
}

function initListeners()
{
    var myRange = document.getElementById("slide");
    myRange.addEventListener("input", function() {updateSlider()}, false);

}