
var slider_default_value = 100, //px
    slider_min_value = 45, //px
    slider_max_value = 600, //px
    mouse_dbclick_delay = 500, //ms

    source_pose = null,
    target_pose = null,
    merge_in_progress = false; // used later 

// activate resize on the navbar
$(function() {
    $( ".resizable" ).resizable({
      handles: "e"
    });
  });


// show/hide nav bar and properties

$(document).keypress(function(e) {

    if (e.which == 110){
        // toggle display of properties
        $( "#properties" ).toggle();
        document.cookie="colibri_properties_display=" + $( "#properties" ).is(":visible");
    }else if(e.which == 116){
        //toggle display of navbar
        $( "#nav" ).toggle();
        document.cookie="colibri_nav_display=" + $( "#nav" ).is(":visible");

    }
});

// activate the slider (for thumbnail preview size)

$(function() {
$('#slider').slider({
        value: slider_default_value,
        min: slider_min_value,
        max: slider_max_value,
        slide: handleSliderChange
    });
});

// action when slider changes
function handleSliderChange(event, slider){

              $('.thumbnail').css('width', slider.value + 'px').css('height', slider.value + 'px');
              document.cookie="colibri_thumbnail_size=" + slider.value;

    }

// on thumbnail click, update the properties view
function colibri_update_properties(selection){
    //alert(selection.attr('title'));
    $('.thumbnail.selectedPose')
    $('#properties_title').val(selection.attr('title'));
    $('#properties_thumbnail_img').attr("src", selection.attr('thumbnail'));
}

// from stackoverflow : THANKS
// get a cookie by his name (k)
function get_cookie(k){return(document.cookie.match('(^|; )'+k+'=([^;]*)')||0)[2]}

var QueryString = function () {
  // This function is anonymous, is executed immediately and 
  // the return value is assigned to QueryString!
  var query_string = {};
  var query = window.location.search.substring(1);
  var vars = query.split("&");
  for (var i=0;i<vars.length;i++) {
    var pair = vars[i].split("=");
        // If first entry with this name
    if (typeof query_string[pair[0]] === "undefined") {
      query_string[pair[0]] = decodeURIComponent(pair[1]);
        // If second entry with this name
    } else if (typeof query_string[pair[0]] === "string") {
      var arr = [ query_string[pair[0]],decodeURIComponent(pair[1]) ];
      query_string[pair[0]] = arr;
        // If third or later entry with this name
    } else {
      query_string[pair[0]].push(decodeURIComponent(pair[1]));
    }
  } 
    return query_string;
}();


function attach_events(){


}

// last action hero part
$( document ).ready(function() {
    console.log(document.cookie);
    //
    // Setting the stage
    //
        $('#mousetooltip').hide();

        // set slider
        var colibri_thumbnail_size = get_cookie("colibri_thumbnail_size");
        if (colibri_thumbnail_size){
            $('#slider').slider('value', colibri_thumbnail_size);
            $('.thumbnail').css('width', colibri_thumbnail_size + 'px').css('height', colibri_thumbnail_size + 'px');
        }
        // set visibility
        var colibri_nav_display = get_cookie("colibri_nav_display");
        if (colibri_nav_display == "false"){
            $( "#nav" ).hide();
        }
        var colibri_properties_display = get_cookie("colibri_properties_display");
        if (colibri_properties_display == "false"){
            $( "#properties" ).hide();
        }
     
        // Variables for the mouse actions
        var DELAY = mouse_dbclick_delay,
        clicks = 0,
        timer = null,
        target = null,
        mouse_down=false,
        source_mouseX = 0,
        merge_factor = 0,
        previous_merge_factor = -1;


    if (QueryString.selectedPose){
        colibri_update_properties($("#pose_" + QueryString.selectedPose));
    }

    // actions on thumbnails

    $(".thumbnail")
    .on("click", function(e){

        clicks++;  //count clicks

        if(clicks === 1) {

            //Update des properties
            //console.log('-click');
            
            colibri_update_properties($(this));
            timer = setTimeout(function() {
                //alert('Single Click'); //perform single-click action
                clicks = 0;  //after action performed, reset counter

            }, DELAY);

        } else {


            clearTimeout(timer);  //prevent single-click action
            console.log('double-click');
            // alert('Double Click');  //perform double-click action
            // Apply pose HERE
            var myO = {"operator":"lfs.colibri_apply_pose", "jsonPose":$(this).attr('jsonPoseB64')};
            var myOStr = JSON.stringify(myO);
            console.log(myO);
            connection.send(myOStr);

            clicks = 0;  //after action performed, reset counter
        }

    })
    .on("dblclick", function(e){
        e.defaultPrevented;  //cancel system double-click event
    })
    .on("mousedown", function(e){
        // checking if it's the middle button (2)
        if (e.which==2){
            // if it is, getting the current position
            // initializing mouse down action
            // setting the merge factor at 0
            // display the tooltip
            source_mouseX = e.pageX;
            mouse_down = true;
            target_pose = $(this).attr('jsonPoseB64');
            merge_factor = 0;
            e.preventDefault();

            // get the current pose and store it
            var myO = {"operator":"lfs.colibri_get_pose", "to":'mouse_down_event'};
            console.log(myO);
            var myOStr = JSON.stringify(myO);
            connection.send(myOStr);

            
            $('#mousetooltip').show().offset({
               left:  e.pageX+10,
               top:   e.pageY+10
            }).html('0%');
            colibri_update_properties($(this));
            
            

        }
    });

    $(document).on("mousemove", function(e){
        if (mouse_down){
            // if the mouse mouve and it's during a mouse_down event
            // update the merge factor

            merge_factor = e.pageX-source_mouseX;
            if (merge_factor<0){
                merge_factor = 0;
            }else if(merge_factor>100){
                merge_factor=100;
            }
            // moving tooltip
            $('#mousetooltip').offset({
               left:  e.pageX+10,
               top:   e.pageY+10
            });
            
            if (source_pose){
                // source pose has been updated ready to perform magics
                if (merge_factor !=  previous_merge_factor ){
                    // if the merge factor is the same, the action should have been send already

                    $('#mousetooltip').html(merge_factor +"%");
                    if (merge_in_progress == false){ 
                        var myO = {"operator":"lfs.colibri_apply_pose", "jsonPose":target_pose, 'initial_pose':source_pose, 'merge_factor':merge_factor};
                        var myOStr = JSON.stringify(myO);
                        console.log(myO);
                        connection.send(myOStr);
                        previous_merge_factor = merge_factor;
                        merge_in_progress = true;
                    }
                }
            }else{
                // source pose is not yet updated (waiting for call back)
                $('#mousetooltip').html("<span class='alert'>Waiting initial pose...</span>");
            }
            // Call Here the update to Blender
            // send initial pose and target pose ?
        }

    }).on("mouseup", function(e){
        if (e.which==2 && mouse_down){
            // if mouse up during a mouse_down option :
            // enf of envent
            mouse_down = false;
            source_pose = null;
            target_pose = null;
            previous_merge_factor = -1;
            console.log("end of middle mouse move")
            $('#mousetooltip').hide();
            // call here final pose ?
        }
    });

    // New pose

    $(".new_pose")
    .on("click", function(e){
        alert(window.location);
        window.location.replace(".?newPose");
    });


});

// right middle click

