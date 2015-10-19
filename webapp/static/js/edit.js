


$('#reloadThumbnail').click(function(){
    //alert($(this).attr('pose'));
    var pose = $(this).attr('pose');
    //connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT", data="'+ pose + '")');
    var myO = {"operator":"lfs.colibri_snapshot", "pose_id":pose};
    var myOStr = JSON.stringify(myO);
    alert(myOStr)
    connection.send(myOStr);
    //location.reload();
});

$('#reloadPose').click(function(){
    //alert($(this).attr('pose'));
    var pose = $(this).attr('pose');
    connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="EXPORT_POSE", data="'+ pose + '")');
    location.reload();
});

$('.applyPose').click(function(){
    //alert($(this).attr('pose'));

    var pose_id = $(this).attr('pose_id');

    // get the pose b64
    $.get( "/pose/" + pose_id +"/getposeb64/", {'countAsApplied':'yes'}, function( data ) {
        //alert(data);
        // connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="APPLY_POSE", data="'+ pose_id + '", jsonPose="' + data + '")');
        var myO = {"operator":"lfs.colibri_apply_pose", "jsonPose":data};
        var myOStr = JSON.stringify(myO);
        alert(myOStr)
        connection.send(myOStr);
    });
    
    // send it


    //var pose = $(this).attr('pose');
    //var jsonPose =  btoa( $("#jsonPose").val() );  
    //alert(jsonPose);
    //connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="APPLY_POSE", data="'+ pose + '", jsonPose="' + jsonPose + '")');
    //location.reload();
});


$('.selectBones').click(function(){
    //alert($(this).attr('pose'));

    var pose_id = $(this).attr('pose_id');

    // get the pose b64
    $.get( "/pose/" + pose_id +"/getposeb64/", {'countAsApplied':'no'}, function( data ) {
        //alert(data);
        connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SELECT_BONES", data="'+ pose_id + '", jsonPose="' + data + '")');
    });
});

$('.saveChanges').change(function(){
    var field = $(this).attr('field');
    var val = $(this).val();
    var pose_id = $('#pose').attr('pose_id');


    $.post( "/pose/" + pose_id, {field: field, val:val }, function( data ) {

    });

});

