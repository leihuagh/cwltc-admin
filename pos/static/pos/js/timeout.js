var timingCode = (function () {
    "use strict";
    //Reset timer when class .timed is used
    // call {{ timeout_url }} when it expires
    // Timeout value in {{ timeout }}
    // console.log("I'm here");

    var timing = {};

    var timer = 0;
    var timeout = 1000;
    var timeoutUrl = "";

    var pingTimer;
    var pingTimeout = "";
    var pingUrl = "";
    var csrf_token = "";
    var terminal = 0;
    var id_message = "";


    timing.abort = function () {
        window.location.replace(timeoutUrl);
    };

    timing.stopTimer = function () {
        clearTimeout(timer);
    };

    timing.startTimer = function (t, url) {
        timeout = t;
        timeoutUrl = url;
        timer = setTimeout(timing.abort, timeout);
    };

    timing.restartTimer = function (){
        clearTimeout(timer);
        timer = setTimeout(timing.abort, timeout);
    };

    $('.timed').on('keyup click', function () {
        timing.stopTimer();
        timer = setTimeout(timing.abort, timeout);
    });

    $('.stop-timer').click(function () {
        timing.stopTimer();
    });


    timing.initPing = function(timeout, url, token, term, idMessage) {
        // Initialise a regular ping message
        pingTimeout = timeout;
        pingUrl = url;
        csrf_token = token;
        terminal = term;
        id_message = idMessage;
        timing.ping();
    };

    timing.stopPing = function () {
        clearTimeout(pingTimer);
    };

    timing.startPing = function () {
        pingTimer = setTimeout(timing.ping, pingTimeout);
    };

    timing.ping = function () {
        // post a message to the server with terminal number
        $.ajax({
            type: "POST",
            url: pingUrl,
            data: 'terminal=' + terminal,
            timeout: timeout,
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader('X-CSRFToken', csrf_token);
            },
            success: function (data, status, xhr) {
                $('#idOfflineMessage').hide();
                $('#idOnlineMessage').show();
                $('#idOnline').text('Online');
                $('.posbutton').show();
                if (data === 'OK') {
                    timing.startPing();
                }else{
                    window.location.replace(data);
                }
            },
            error: function (data, status, xhr) {
                $('#idOfflineMessage').show();
                $('#idOfflineMessage').text('Sorry, the server is temporarily available. Please try later');
                $('#idOnline').text('OffLine');
                $('.posbutton').hide();
                timing.startPing();
            }
        });
    };
    return timing;
})();
