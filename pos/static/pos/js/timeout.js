//Reset timer when class .timed is used
// call {{ timeout_url }} when it expires
// Timeout value in {{ timeout }}
// console.log("I'm here");

var timer = 0;
var timeout = 1000;
var timeoutUrl = "";

function abort(){
    window.location.replace(timeoutUrl);
}

function stopTimer(){
    clearTimeout(timer);
}

function startTimer(t, url){
    timeout = t;
    timeoutUrl = url;
    timer = setTimeout(abort, timeout);
}
//
// $(".timed").click(function () {
//     timer = setTimeout(abort, timeout);
// });

$('.timed').on('keyup click', function(){
    stopTimer();
    timer = setTimeout(abort, timeout);
});

$('.stop-timer').click(function () {
    stopTimer();
});