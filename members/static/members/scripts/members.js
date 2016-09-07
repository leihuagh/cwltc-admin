// Requires ajaxUrl to be set
$(document).ready(function () {
    console.log(ajaxUrl)
    $('#people').dataTable({
        "ajax": {
            "url": ajaxUrl,
            "type": "POST",
            "data": function (d) {
                d.categories = $('#id_categories').val();
                d.membership_year = $('#id_membership_year').val();
                d.paystate = $('#id_paystate').val();
                                }
                },
        "columns": [ null,null,null,null,
            {
                "render": function (data, type, row, meta) {
                    if (type === 'display') {
                        return $('<a>')
                            .attr('href', '/' + data)
                            .text(data)
                            .wrap('<div></div>')
                            .parent()
                            .html();
                    } else {
                        return data;
                    }
                }
            }
        ]
    });
});

$('.trigger').change(function () {
    console.log("Change!")  // sanity check
    $('#people').DataTable().ajax.reload();
    //ajax_post();
});


//// from django documentation
//function csrfSafeMethod(method) {
//    // these HTTP methods do not require CSRF protection
//    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
//}
//$.ajaxSetup({
//    beforeSend: function (xhr, settings) {
//        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
//            xhr.setRequestHeader("X-CSRFToken", $("input[name='csrfmiddlewaretoken']").val());
//        }
//    }
//})

// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// from django documentation
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
})

// AJAX for posting
function ajax_post() {
    console.log("AJAX post"); // sanity check
    $.post(".", {
        membership_year: $('#id_membership_year').val(),
        categories: $('#id_categories').val(),
        paid: $('#id_paid').checked,
        unpaid: $('#id_unpaid').checked
    }
    ).done(function (json) {

        var data= json["data"];
        //var search = json["search"];
        $("#people").dataTable(json);
        //$("#people").DataTable().search(search).draw();
    }
    ).fail(function (xhr, errmsg, err) {
        $('#results').html("<div class='alert-box alert radius' data-alert>Oops! We have encountered an error: " + errmsg +
            " <a href='#' class='close'>&times;</a></div>"); // add the error to the dom
        console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
    }
    );
}
