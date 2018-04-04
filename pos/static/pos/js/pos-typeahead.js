function bind_typeahead(typeahead_id, setPerson, adult) {

    // var people = new Bloodhound({
    //     datumTokenizer: Bloodhound.tokenizers.whitespace,
    //     queryTokenizer: Bloodhound.tokenizers.whitespace,
    //     remote: {
    //         url: '/ajax/people/?term=%QUERY&adult=true',
    //         wildcard: '%QUERY'
    //     }
    // });

    var lastItem;
    var qualifier = '';
    if (adult){
        qualifier = '&adult=true';
    }

    // Initializing the typeahead with remote dataset
    $(typeahead_id).typeahead({
        minLength: 3,
        hint: true,
        highlight: true
    },
        {
            name: 'people',
            displayKey: "value",
            // source: people.ttAdapter(),
            source: function(query, syncResults, asyncResults) {
                $.get('/ajax/people/?term=' + query + qualifier, function (data) {
                    asyncResults(data);
                });
            },
            limit: 10
        }).focus();

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
};