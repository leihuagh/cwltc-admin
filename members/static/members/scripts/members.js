//$('#people').dataTable({
//    "lengthMenu": [[10, 15, 25, 50, -1], [10, 15, 25, 50, "All"]]
//});
$(document).ready(function () {
    $('#people').dataTable({
        "ajax": {
            "url": "/people/",
            "type": "POST",
            "data": function( d ) {
                d.csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']").val();
                d.categories = $('#id_categories').val();
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

$('#id_categories').change(function () {
    console.log("Change!")  // sanity check
    $('#people').DataTable().ajax.reload();
});

// from django documentation
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", $("input[name='csrfmiddlewaretoken']").val());
        }
    }
})

// AJAX for posting
function ajax_post() {
    console.log("AJAX post") // sanity check
    $.post("/", {
        csrfmiddlewaretoken: $("input[name='csrfmiddlewaretoken']").val(),
        categories: $('#id_categories').val()
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
