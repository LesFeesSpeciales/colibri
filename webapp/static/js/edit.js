


$('#reloadThumbnail').click(function(){
    //alert($(this).attr('pose'));
    var pose = $(this).attr('pose');
    connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT", data="'+ pose + '")');
    location.reload();
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
    $.get( "/pose/" + pose_id +"/getposeb64/", {}, function( data ) {
        //alert(data);
        connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="APPLY_POSE", data="'+ pose_id + '", jsonPose="' + data + '")');
    });
    // send it


    //var pose = $(this).attr('pose');
    //var jsonPose =  btoa( $("#jsonPose").val() );  
    //alert(jsonPose);
    //connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="APPLY_POSE", data="'+ pose + '", jsonPose="' + jsonPose + '")');
    //location.reload();
});

$('.saveChanges').change(function(){
    var field = $(this).attr('field');
    var val = $(this).val();
    var pose_id = $('#pose').attr('pose_id');


    $.post( "/pose/" + pose_id, {field: field, val:val }, function( data ) {

    });

});