//Reset timer when class .timed is used
// call {{ timeout_url }} when it expires
// Timeout value in {{ timeout }}
console.log("I'm here");

$(document).ready(function () {
    function abort(){
        window.location.replace("{{ timeout_url }}")
    }

    var timer = setTimeout(abort, {{ timeout }});
    $(".timed").tap(function () {
        if (timer === 0){
            clearTimeout(timerId);
            }
        timer = setTimeout(abort, {{ timeout }});
    });
});

$(document).bind("mobileinit", function () {
    // Stop jQuery Mobile messing with our links
    $.mobile.linkBindingEnabled = false;
});