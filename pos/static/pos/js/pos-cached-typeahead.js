
function bind_typeahead(typeahead_id, setPerson, filter) {
    "use strict";
    // https://digitalfortress.tech/tutorial/smart-search-using-twitter-typeahead-bloodhound/
    var people = new Bloodhound({
        datumTokenizer: function(d) {return Bloodhound.tokenizers.whitespace(d.value);},
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        prefetch: {
            url: '/ajax/adults'
        },
        dupDetector: function(remoteMatch, localMatch){
            return remoteMatch.id === localMatch.id;
        },
        // local: [{id: 1, value: 'zzzz'}],
        // identify: function(obj) {return obj.value;}
        remote: {
            url: '/ajax/people/?term=%QUERY&adult=true',
            wildcard: '%QUERY'
        }
    });


    function loadPeople(){
        $.get('/ajax/adults', function (data) {
            localStorage.setItem('people', data);
        });
    }

    function lookup(query, syncResults, asyncResults){
        // $.get('/ajax/people/?term=' + query + qualifier, function (data) {
        //     asyncResults(data);
        // });
        // syncResults(localStorage.getItem('people'));
        syncResults([{id: 1, value: 'zzzz'}]);
    }


    var lastItem;
    var qualifier = '';
    if (filter==='adults') {
        qualifier = '&adult=true';
    }else if (filter==='members') {
        qualifier = '&members=true';
    }

    $(typeahead_id).typeahead({
        hint: true,
        highlight: true,
        minLength: 3
    },
    {
        name: 'people',
        displayKey: 'value',
        source: people   // Bloodhound instance is passed as the source
    });




    // Selecting an item sets person_id
    $(typeahead_id).bind('typeahead:select', function (event, item) {
        setPerson(item);
    });

    // Record selected item when cursor changes it
    $(typeahead_id).bind('typeahead:cursorchange', function (event, item) {
        lastItem = item;
    });

    // Autocomplete sets the item
    $(typeahead_id).bind('typeahead:autocomplete', function (event, item) {
        setPerson(item);
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
                    setPerson(lastItem);
                }
            }
        }
    });
}