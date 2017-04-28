﻿$(document).ready(function () {
    $('#person_id').val("")
   
    // constructs the suggestion engine
    var people = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.whitespace,
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/ajax/people/?term=%QUERY',
            wildcard: '%QUERY'
        }
    });

    // Initializing the typeahead with remote dataset
    $('.typeahead').typeahead({
        minLength: 3,
        hint: true,
        highlight: true},
        {
            name: 'people',
            displayKey: "value",
            source: people.ttAdapter(),
            limit: 10
        }).focus();
 
    // Selecting an item sets #person_id
    $('.typeahead').bind('typeahead:select', function (event, item) {
        $('#person_id').val(item.id);
        $('#submit').trigger('click');
        return item
    });

    // Record selected item when cursor changes it
    $('.typeahead').bind('typeahead:cursorchange', function (event, item) {
        if (typeof item == 'undefined') {
            $('#person_id').val("");
        } else {
            $('#person_id').val(item.id)
        }
    });

    // Autocomplete sets the item
    $('.typeahead').bind('typeahead:autocomplete', function (event, item) {
        $('#person_id').val(item.id);
        console.log("autocomplete");
    });

    // http://bwbecker.github.io/blog/2015/08/29/pain-with-twitter-typeahead-widget/

    // Enter key behaviour
    $('.typeahead').on('keydown', function (e) {
        if (e.keyCode == 13) {
            // if no suggestions ignore the keypress 
            if ($('.tt-suggestion').length == 0) {
                e.preventDefault();
            } else {
                if ($('#person_id').val() === '') {
                    // Trigger the default (first) suggestion
                    $('.tt-suggestion:first-child').trigger('click');
                } else {
                    // The suggestion they chose with arrow keys
                    $('#submit').trigger('click');
                }
            }
        }
    });
});

