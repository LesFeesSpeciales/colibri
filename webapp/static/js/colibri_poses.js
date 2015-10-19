

$(function() {
    $( ".resizable" ).resizable({
      handles: "e"
    });
  });


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


$(function() {
$('#slider').slider({
        value: 100,
        min: 45,
        max: 340,
        slide: handleSliderChange
    });
});

function handleSliderChange(event, slider){

              $('.thumbnail').css('width', slider.value + 'px').css('height', slider.value + 'px');
              document.cookie="colibri_thumbnail_size=" + slider.value;

    }

function colibri_update_properties(selection){
    //alert(selection.attr('title'));
    $('#properties_title').val(selection.attr('title'));
    $('#properties_thumbnail_img').attr("src", selection.attr('thumbnail'));
}

function get_cookie(k){return(document.cookie.match('(^|; )'+k+'=([^;]*)')||0)[2]}


// click and double click on thumbnails
$( document ).ready(function() {
    console.log(document.cookie);

    
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
 

    var DELAY = 500,
    clicks = 0,
    timer = null,
    target = null,
    mouse_down=false,
    source_mouseX = 0,
    merge_factor = 0;


    $(".thumbnail")
    .on("click", function(e){

        clicks++;  //count clicks

        if(clicks === 1) {

            //Update des properties
        console.log('-click');
        colibri_update_properties($(this));
            timer = setTimeout(function() {

                //alert('Single Click'); //perform single-click action
                clicks = 0;  //after action performed, reset counter

            }, DELAY);

        } else {


            clearTimeout(timer);  //prevent single-click action
            console.log('double-click');
            // alert('Double Click');  //perform double-click action
            // appl pose

            clicks = 0;  //after action performed, reset counter
        }

    })
    .on("dblclick", function(e){
        e.defaultPrevented;  //cancel system double-click event
    })
    .on("mousedown", function(e){
        if (e.which==2){
            source_mouseX = e.pageX;
            mouse_down = true;
            merge_factor = 0;
            e.preventDefault();
            $('#mousetooltip').show().offset({
               left:  e.pageX+10,
               top:   e.pageY+10
            }).html('0%');
        }
    });

    $(document).on("mousemove", function(e){
        if (mouse_down){
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
            }).html(merge_factor +"%");
            console.log(merge_factor);
        }

    }).on("mouseup", function(e){
        if (e.which==2 && mouse_down){
            mouse_down = false;
            console.log("end of middle mouse move")
            $('#mousetooltip').hide();
        }
    });


});

// right middle click

