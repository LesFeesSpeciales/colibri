


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

$('#applyPose').click(function(){
    //alert($(this).attr('pose'));
    var pose = $(this).attr('pose');
    var jsonPose =  btoa( $("#jsonPose").val() );  
    alert(jsonPose);
    connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="APPLY_POSE", data="'+ pose + '", jsonPose="' + jsonPose + '")');
    location.reload();
});