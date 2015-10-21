var port = 8137
var connection = new WebSocket('ws://localhost:' + port);


connectionTimeOut = setTimeout(function (){
    console.log("socket timeout");
    $('#connection_msg').html('<span class="alert">Connection timeout on port '+port+'.</span>')

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
    $('#connection_msg').html('<span class="alert">Connection closed on port '+port+'.</span>')
    clearTimeout(connectionTimeOut);
};

 
connection.onerror = function (error) {
    console.log('WebSocket Error ' + error);
    $('#connection_msg').html('<span class="alert">Connection error on port '+port+'.</span>')
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
            // SIMPLE BLENDER PING TO GET FILE of the connection
              $('#connection_msg').html("connected to <strong>" + obj.filename + "<strong>");

         }else if (obj.operator == "lfs.colibri_get_pose" && obj.to == 'mouse_down_event'){
            // SIMPLET GET POSE FOR THE MOUSE_DOWN MERGE POSES
            source_pose = obj.poseB64;

         }else if (obj.operator == "lfs.colibri_get_pose" && obj.to == 'update_pose'){
            // UPDATING POSE FROM BLENDER TO DB
            $("#properties_update_pose").html("Updating db...");
            //alert(obj.pose_id);
            $("#pose_" + obj.pose_id).attr("jsonPoseB64", obj.poseB64);
            // update de la db
            var field = 'json';
            var val = obj.poseB64;
            var pose_id = obj.pose_id;


            $.post( "/pose/" + pose_id, {field: field, val:val, source_file:obj.source_file }, function( data ) {

            });

            colibri_update_properties($("#pose_" + obj.pose_id));

            $("#properties_update_pose").html("Updated. Update again");

            if ($("#pose_" + obj.pose_id).hasClass("emptyPose")){
                $("#pose_" + obj.pose_id).removeClass("emptyPose");
            }

         }else if (obj.operator == "lfs.colibri_apply_pose"){
            // APPLY POSE CALL BACK TO AVOID APPLYING TO MANY TIMES THE POSES
            merge_in_progress = false;
         }else if (obj.operator == "lfs.colibri_snapshot"){
            // APPLY POSE CALL BACK TO AVOID APPLYING TO MANY TIMES THE POSES
            
            var pose_id = $('#properties_pose_id').val();
            console.log("Pose #" + pose_id + " thumbnail updated");
            var d = new Date();
            $('#properties_thumbnail_img').attr('src', '/static/content/' + pose_id + '.png?'+d.getTime());
            $('#pose_' + pose_id).css("background-image", "url('/static/content/" + pose_id + ".png?" +d.getTime() +"')"); 
            $('#properties_update_thumbnail').html("Thumbnail updated");

         }else{
            // UNEXEPECTED CALLBACK
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