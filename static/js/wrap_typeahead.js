/* globals Bloodhound */

function wrap_typeahead(typeahead_id, url, query, callback) {
    'use strict';

    var lastItem;
    var data = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.whitespace,
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: url + '?term=%QUERY' + query,
            wildcard: '%QUERY'
        }
    });

    // Initializing the typeahead with remote dataset
    $(typeahead_id).typeahead({
        minLength: 3,
        hint: true,
        highlight: true
    },
        {
            name: 'data',
            displayKey: "value",
            source: data.ttAdapter(),
            limit: 10
        }).focus();


    $('.tt-suggestion').on('click', function(e) {
        console.log('click');
    });
    // Selecting an item calls the function
    $(typeahead_id).bind('typeahead:select', function (event, item) {
        callback(item);
    });

    // Record selected item when cursor changes it
    $(typeahead_id).bind('typeahead:cursorchange', function (event, item) {
        lastItem=item;
    });

    // Autocomplete sets the item
    $(typeahead_id).bind('typeahead:autocomplete', function (event, item) {
        callback(item);
    });

    // http://bwbecker.github.io/blog/2015/08/29/pain-with-twitter-typeahead-widget/

    // Enter key behaviour
    $(typeahead_id).on('keydown', function (e) {
        if (e.keyCode === 13) {
            // if no suggestions ignore the keypress 
            if ($('.tt-suggestion').length === 0) {
                e.preventDefault();
            } else {
                if (lastItem === undefined) {
                    // Trigger the default (first) suggestion
                    $('.tt-suggestion:first-child').trigger('click');
                } else {
                    // The suggestion they chose with arrow keys
                    callback(lastItem);
                }
            }
        }
    });
}