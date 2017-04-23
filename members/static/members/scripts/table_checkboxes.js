// Handle checkboxes in tables to select rows
$(document).ready(function () {
    countChecked();
   // $('#id_search').onclick = doSearch;
    document.getElementById('id_search').onclick = doSearch;
    document.getElementById('id_loader').style.display = 'none';
    document.getElementById('id_action_form').style.visibility = 'visible';
    //$('#id_table_panel').show();
});

$(window).load(function () {
    //document.getElementById('id_table_panel').style.display = 'none';
   // $('#id_table_panel').hide();
});

// toggle / untoggle as checkboxes in the list
function toggle(source) {
    var checkboxes = document.getElementsByName('selection');
    var count=0
    for (i = 0; i < checkboxes.length; i++)
        checkboxes[i].checked = source.checked;
    countChecked();
}

// Count the number of checked rows
function countChecked() {
    var count = document.querySelectorAll('.rowcheckbox:checked').length;
    document.getElementById('id-count').innerText = count
    var goDisabled = (count === 0);
    $('#id_action').prop('disabled', goDisabled);
    $('#id_go').prop('disabled', goDisabled);
}

function doSearch() {
    $('#id_loader').show();
    //$('#id_table_panel').hide();
   
    //document.getElementById('id_table_panel').style.visibility = 'hidden';
    document.getElementById('id_action_form').style.visibility = 'hidden';
    document.getElementById('id_loader').style.display = 'inherit';
    document.getElementById('id_search_form').submit();
}