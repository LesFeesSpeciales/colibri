


$('#reloadThumbnail').click(function(){
    //alert($(this).attr('pose'));
    var pose = $(this).attr('pose');
    connection.send('bpy.ops.lfs.pose_lib("EXEC_DEFAULT", action="SNAPSHOT", data="'+ pose + '")');
    location.reload();
});