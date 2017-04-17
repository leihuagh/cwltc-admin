// Handle checkboxes in tables to select rows
$(document).ready(function () {
    countChecked();
    console.log("ready");
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