'use strict'

// Handle checkboxes in tables to select rows
$(document).ready(function () {
    countChecked();
    if ($('#id_search').length){
        $('#id_search').onclick = doSearch;
    }
    $('#id_action_form').show();
    document.getElementById('id_search').onclick = doSearch;
    //document.getElementById('id_loader').style.display = 'none';
    document.getElementById('id_action_form').style.visibility = 'visible';
    //$('#id_table_panel').show();
});


// toggle / untoggle all checkboxes in the list
function toggle(source) {
    var checkboxes = document.getElementsByName('selection');
    for (var i = 0; i < checkboxes.length; i++){
        checkboxes[i].checked = source.checked;
    }
    countChecked();
}

// Count the number of checked rows
function countChecked() {
    var count = document.querySelectorAll('.rowcheckbox:checked').length;
    
    var goDisabled = ((count === 0) | (count > 1000));
    if (count > 5000) {
        count = "Too many selected";
    }
    $('#id-count').text(count)
    $('#id_action').prop('disabled', goDisabled);
    $('#id_go').prop('disabled', goDisabled);
}

function doSearch() {
    $('#id_loader').show();
    $('#id_action_form').hide();
    $('#id_search_form').submit();
}