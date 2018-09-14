// Version 3 Fully support offline working
var posCode = (function (){
    "use strict";

    var pos = {};

    // DOM objects
    var receiptArea = document.getElementById('receipt-area');
    var peopleTable = document.getElementById('peopleTable');

    var payClass = $('.buttons-active');
    var exitClass = $('.button-exit');

    var items;
    var layouts;

    var receipt;
    var total;
    var formattedTotal;
    var line;
    var online = false;

    // Django context variables
    var layoutId;
    var isAttended = false;
    var urls;

    var personId;
    var person;
    var personName;
    var personList;
    var touched = false;


    var pingTimer;
    var pingTimeout = "";
    var pingUrl = "";
    var terminal = 0;

    var timer;
    var timeout = 12000000;
    var ajaxTimeout = 20000;

    /* Public methods*/
    pos.init = function (is_attended, person_id, person_name, layout_id, csrf_token, terminal, url_dict) {
        isAttended = is_attended;
        personId = person_id;
        personName = person_name;
        layoutId = layout_id;
        urls = JSON.parse(url_dict);
        payClass.hide();
        exitClass.hide();
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader('X-CSRFToken', csrf_token);
            }
        });
        //localStorage.clear();
        initPing(timeout, urls.ping, terminal);
        loadData();
        newReceipt();
        clearTimeout(timer);

        $(".touch").on('touchstart', function(event) {
            event.currentTarget.classList.add('posbutton-down');
            event.preventDefault();
        });


        $(".item-button").on('touchstart click', function(event) {
            event.currentTarget.classList.add('posbutton-down');
            handleTouch(event, 'item');
        });

        $(".item-button").on('touchend click', function(event) {
            event.currentTarget.classList.remove('posbutton-down');
            event.preventDefault();
        });

        $('.timeout').on('touchstart click keydown', function () {
            clearTimeout(timer);
            timer = setTimeout(pos.logOut, timeout);
            console.log('Set timer');
        });

        $('.stop-timer').on('touchstart click', function () {
            clearTimeout(timer);
            console.log('clear timer');
        });


    };

    // Common code to make touch events as fast as click
    // Can be used for touch start or touchend
    pos.touch = function(event, action) {
        handleTouch(event, action);
    };

    function handleTouch(event, action) {
        event.preventDefault();
        if (event.type === 'click') {
            if (!touched) {
                doAction(event, action);
            }
            touched = false;
        } else {
            touched = true;
            doAction(event, action);
        }
    }

    function doAction(event, action){
        if (action) {
            if (action === 'item') {
                pos.itemAdd(event.currentTarget.item);
            } else {
                action();
            }
        }
    }

    pos.logOut = function(){
        personId = '';
        personName = '';
        hideModals();
        document.activeElement.blur();
        $("input").blur();
        pos.showPage('#pageStart');
    };

    pos.href = function(href){
        clearTimeout(timer);
        window.location.replace(href);
    };

    pos.showPage = function(pageId){
        $('.page').hide();
        if (pageId === '#pagePos') {
          $('#idLogoBanner').hide();
        }else{
          $('#idLogoBanner').show();
        }
        $(pageId).show();
        stopPing();

        document.activeElement.blur();
        switch (pageId) {
            case '#pageStart':
                startPing();
                break;
            case '#pageUser':
               $('#userNameInput').val('').focus();
               break;
            case '#pagePassword':
                $('#passwordError').hide();
                $('#passwordPin').val('').focus();
                $('#passwordInput').val('');
                break;
            case '#pageResetPin':
                $('#resetForm').show();
                $('#resetDone').show();
                $('#resetPostCode').val('').focus();
                $('#resetPhone').val('');
                $('#resetActionArea').hide();
                $('#resetError').text('');
                $('#resetGo').hide();
                break;
            case '#pageSelectMember':
                $('#selectNameInput').val('');
        }
    };

    pos.startApp = function(){
        isAttended = false;
        if (personId) {
            $('.personName').text(personName);
            $('.personId').val(personId);
            pos.showMenu();
        }else{
            pos.showPage('#pageStart');
        }
    };

    pos.startAttended = function() {
        isAttended = true;
        personName = 'Attended mode';
        personId = '';
        $('.personName').text(personName);
        $('.personId').val(personId);
        pos.newReceipt();
    };

    pos.getPin = function(person) {
        if (person){
            personId = person.id;
            personName = person.value;
        }
        $('.personName').text(personName);
        $('.personId').val(personId);
        $('.typeahead').typeahead('val', '');
        pos.showPage('#pagePassword');
        $('#idPinInput').val('').focus();
        $('#idPasswordInput').val('');
    };

    pos.submitPostCode = function() {
        var formData = $('#resetForm').serialize();
        $.ajax({
            type: 'POST',
            url: urls.postCode,
            data: formData,
            timeout: ajaxTimeout,
            success: function (response) {
                if (response === 'OK'){
                    $('#resetForm').hide();
                    $('#resetError').text('');
                    $('#resetActionArea').show();
                    $('#resetPin').val('').focus();
                    $('#resetGo').hide();
                } else {
                    $('#resetError').text(response);
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                setOffline();
                pos.logOut();
            }
        });
    };

    pos.submitPin = function() {
        var formData = $('#resetPinForm').serialize();
        $.ajax({
            type: 'POST',
            url: urls.setPin,
            data: formData,
            timeout: ajaxTimeout,
            success: function (response) {
                pos.showPage('#pagePassword');
            },
            error: function (xhr, textStatus, errorThrown) {
                setOffline();
                pos.logOut();
            }
        });
    };

    pos.submitPassword = function() {
        //var data = "person_id=" + personId + '&pin=' + $('#passwordPin').val() + '&password=' + $('#passwordInput').val();
        var formData = $('#idPasswordForm').serialize();
        var query = parseQuery(formData);
        $('#menuSupervisor').hide();
        if (online){
            $.ajax({
                type: 'POST',
                url: urls.password,
                data: formData,
                timeout: ajaxTimeout,
                success: function (response) {
                    if (response.authenticated){
                        setOnline();
                        if (query.pin){
                            localStorage.setItem('id:' + query.person_id, btoa(query.pin));
                        }
                        if (response.supervisor){
                            $('#menuSupervisor').show();
                        }
                        pos.showMenu();
                    } else {
                        console.log(response);
                        $('#passwordError').show();
                        $('#passwordPin').val('').focus();
                        $('#passwordInput').val('');
                    }
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.log(textStatus + ' ignore password');
                    setOffline();
                    testOfflinePin(query);
                }
            });
        } else {
            testOfflinePin(query);
        }
    };

    pos.showMenu = function(){
        pos.showPage('#pageMenu');
    };

    pos.transactionsPerson = function(person){
        pos.transactions(person.id);
    };

    pos.transactions = function(id) {
        clearTimeout(timer);
        $('.page').hide();
        var url;
        if (id === 'all'){
            url = urls.transactions;
        }else if(id === 'cash'){
            url = urls.transactionsCash;
        }else if (personId === -1 || id === 'comp') {
            url = urls.transactionsComp;
        }else if(id === 'member'){
            pos.showPage('#pageSelectMember');
            return;
        }else {
            url = urls.transactionsPerson.replace('9999', personId);
        }
        window.location.href = url + '?id=' + personId;
    };


    function testOfflinePin(query){
        // test submitted query against stored offline pin
        // if its present and matches start pos
        // if present and wrong -> error
        // if not present, start pos anyway
        var pin = localStorage.getItem('id:' + query.person_id);
        if (pin){
            if (atob(pin) === query.pin){
                console.log('Good offline pin');
                pos.showMenu();
            } else {
                console.log('Bad offline pin');
                pos.startApp();
            }
        } else {
            console.log('Ignore offline pin');
            pos.showMenu();
        }
    }

    pos.newReceipt = function(layoutId){
        newReceipt();
        if (layoutId){
            applyLayout(layoutId);
        }
        pos.showPage('#pagePos');
    };

    pos.itemAdd = function (item) {
        // Add item to receipt array
        var receiptItem = {};
        receiptItem.id = item.id;
        receiptItem.lineId = 'line_' + line;
        line++;
        receiptItem.description = item.description;
        receiptItem.sale_price = item.sale_price;
        receiptItem.cost_price = item.cost_price;
        receiptItem.price = Math.fround(parseFloat(receiptItem.sale_price)*100);
        receipt.push(receiptItem);
        createTable(receipt);
    };

    pos.itemRemove = function (target) {
        var index;
        for (index = 0; index < receipt.length; ++index) {
            if (receipt[index].lineId === target) {
                receipt.splice(index, 1);
                createTable(receipt);
                return;
            }
        }
    };

    pos.pay = function () {
        // initiate payment sequence
        if (isAttended) {
            personList = [];
            $('#attended_total').text(formattedTotal);
            $('#attended_modal').modal('show');
        } else {
            personList = [{'id': personId, 'name': personName, 'amount': total}];
            $('#member_total').text(formattedTotal);
            $('#member_name').text(personName);
            $('#member_modal').modal('show');
        }
        $('#member_search').val('');
        $('.typeahead').typeahead('val', '');
    };

    pos.selectMember = function () {
        console.log('selected');
    };

    pos.cash = function () {
        hideModals();
        personList = [];
        sendTransaction('cash');
    };

    pos.commitSingle = function () {
        // charge to single logged on member
        hideModals();
        personList = [{'id': personId, 'name': personName, 'amount': total}];
        sendTransaction('account');
    };

    pos.commit = function () {
        // charge to list of members
        hideModals();
        sendTransaction('account');
    };

    pos.account = function () {
        // Select first member in attended mode
        personList = [];
        showSplit(true);
        $('#title_1').text('Charge');
        $('#title_total').text(formattedTotal);
        $('#title_2').text("to member's account");
        $('#member_search').typeahead('val', '').focus();
    };

    pos.split = function () {
        // initiate a split across members
        personList = [{'id': personId, 'name': personName}];
        showSplit(false);
    };

    pos.addMember = function() {
        // add member button on split sale modal
        showSplit(true);
        $('#member_search').typeahead('val', '').focus();
    };

    pos.selectedPerson = function (p) {
        // user selected a person through the type ahead
        person = p;
        personList.push({'id': p.id, 'name': p.value});
        showSplit(false);
        if (isAttended && personList.length === 1) {
            $('#title_1').text('Charge');
            $('#title_total').text(formattedTotal);
            $('#title_2').text("to member's account");
        }
    };

    pos.back1 = function() {
        // back from select member dialog
        hideModals();
        switch(personList.length) {
            case 0:
                $('attended_modal').modal('show');
                break;
            case 1:
                if (isAttended) {
                    pos.resume();
                } else {
                    $('#member_modal').modal('show');
                }
                break;
            default:
                showSplit(false);
        }
    };

    pos.resume = function () {
        hideModals();
    };

    function hideModals(){
        $('#pay_modal').modal('hide');
        $('#attended_modal').modal('hide');
        $('#member_modal').modal('hide');
        $('#select_modal').modal('hide');
    }



    function showSplit(withSelect) {
        // calculate split amounts and show list of members with amounts
        // withSelect controls whether typeahead or buttons are shown
        var row;
        var cell;
        var i;
        var tableBody = document.createElement('tbody');
        while (peopleTable.firstChild) {
            peopleTable.removeChild(peopleTable.firstChild);
        }
        if (personList.length === 0) {
            row = document.createElement('tr');
            cell = document.createElement('td');
            cell.className = "person-name";
            cell.appendChild(document.createTextNode('No members selected'));
            row.appendChild(cell);
            tableBody.appendChild(row);
        } else {
            // calculate the split amounts
            var splitPence = Math.floor(total/ personList.length);
            var firstPence = splitPence;
            var splitTotal = splitPence * personList.length;
            for (i = 0; i < personList.length; i ++) {
                personList[i].amount = splitPence;
            }
            if (splitTotal < total) {
                i = 0;
                while (splitTotal < total) {
                    personList[i].amount += 1;
                    i += 1;
                    splitTotal += 1;
                }
            }
            for (i = 0; i < personList.length; i ++) {
                row = document.createElement('tr');
                cell = document.createElement('td');
                cell.className = "person-name";
                cell.appendChild(document.createTextNode(personList[i].name));
                row.appendChild(cell);
                cell = document.createElement('td');
                cell.className = "person-amount";
                cell.appendChild(document.createTextNode('£ ' + (personList[i].amount / 100).toFixed(2)));
                row.appendChild(cell);
                tableBody.appendChild(row);
            }
        }
        peopleTable.appendChild(tableBody);
        // default header message gets overwritten for the first person
        $('#title_1').text('Split');
        $('#title_total').text(formattedTotal);
        $('#title_2').text("between members");
        if (withSelect) {
            $('#add_member_typeahead').show().focus();
            $('#pay_buttons').hide();
        } else {
            $('#add_member_typeahead').hide();
            $('#pay_buttons').show();
        }
        hideModals();
        $('#select_modal').modal('show');
    }

    function sendTransaction(payType) {
        // post the transaction to the server
        // the response is the next screen to show
        clearTimeout(timer);
        var stamp = new Date().getTime();
        var payObj = {
            'pay_type': payType,
            'people': personList,
            'total': total,
            'stamp': stamp,
            'layout_id': layoutId
        };
        receipt.push(payObj);
        var transaction = JSON.stringify(receipt);
        $.ajax({
            type: "POST",
            url: urls.sendTransaction,
            data: transaction,
            dataType: 'text',
            tryCount: 0,
            retryLimit: 1,
            timeout: ajaxTimeout,
            success: function (response) {
                var result = response.split(';');
                if (result[0] === 'Saved') {
                    console.log('Transaction saved');
                    $('#idLastTransaction').text(result[1]);
                    $('#idLastTotal').text(result[2]);
                    $('#menuLastTransaction').text('Last purchase: £' + result[2]);
                }else if (result[0] === 'Exists'){
                    console.log('Transaction exists with id ' + result[1]);
                }else{
                    console.log('Unknown server response');
                }
                pos.startApp();
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log ('Error {xhr} {textStatus}');
                saveTransaction(transaction, stamp);
                $('#idLastTransaction').text('local');
                $('#idLastTotal').text(payObj.total);
                $('#menuLastTransaction').text('Last purchase: £ ' + payObj.total/100);
                pos.startApp();
            }
        });
    }

    function parseQuery(queryString) {
        var query = {};
        var pairs = (queryString[0] === '?' ? queryString.substr(1) : queryString).split('&');
        for (var i = 0; i < pairs.length; i++) {
            var pair = pairs[i].split('=');
            query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
        }
    return query;
}
    function savePin(id, pin){
        // Save obfuscated pin in local storage
        var key = 'Id:' + id;
        localStorage.setItem(key, btoa(pin));
    }

    function checkPin(id, pin){
        var p = localStorage.getItem('Id:' + id);
        if (p){
            return atob(p) === pin;
        }else{
            return false;
        }
    }


    function saveTransaction(trans, stamp){
        // Save transaction in local storage
        var key = 'Trans:' + stamp;
        localStorage.setItem(key, trans);
        var contents = getContents();
        contents.push(key);
        localStorage.setItem('contents', JSON.stringify(contents));
        $('#idSaved').text(contents.length);
    }


    function getContents(){
        // Return the list of transaction keys for locally saved transactions
        var jsonContents = localStorage.getItem('contents');
        if (jsonContents) {
            return JSON.parse(jsonContents);
        }else{
            return [];
        }
    }

    function removeTransaction(){
        var contents = getContents();
        localStorage.removeItem(contents[0]);
        console.log('removed ' + contents[0]);
        contents.splice(0, 1);
        localStorage.setItem('contents', JSON.stringify(contents));
        $('#idSaved').text(contents.length);
        return contents;
    }

    pos.recoverTransactions = function(){
        recoverTransactions();
    };

    function recoverTransactions(){
        // If there are saved transactions, try to send them to the server
        // The server will ensure that transactions are only saved once
        // stop if an error occurs
        var contents = getContents();
        if (contents.length > 0){
            $.ajax({
                type: "POST",
                url: urls.sendtransaction,
                data: localStorage.getItem(contents[0]),
                dataType: 'text',
                timeout: ajaxTimeout,
                success: function(response){
                    console.log(response);
                    var result = response.split(';');
                    if (result[0] === 'Saved' || result[0] === 'Exists') {
                        contents = removeTransaction();
                        if (contents.length > 0){
                            console.log('Next item ' + contents[0]);
                            this.data = localStorage.getItem(contents[0]);
                            $.ajax(this);
                        }
                    }else{
                        console.log('Server error - abort recovery');
                    }
                },
                error: function(xhr, textStatus, errorThrown){
                    console.log('Error ' + xhr + ' ' + textStatus + 'abort recovery');
                }
            });
        }
    }


    function newReceipt() {
        receipt = [];
        line = 0;
        createTable(receipt);
    }


    function loadData() {
        // Load items, colours and all layouts from the server
        $.ajax({
            type: 'GET',
            url: urls.items,
            timeout: ajaxTimeout,
            success: function (response) {
                console.log('Saving ' + this.url);
                localStorage.setItem('data', JSON.stringify(response));
                processData();
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log('Error' + this.url);
                processData();
            }
        });
    }


    function processData() {
        // Creates an item dictionary and a layout dictionary
        var data = JSON.parse(localStorage.getItem('data'));
        if (data) {
            var colours = JSON.parse(data.colours);
            var itemArray = JSON.parse(data.items);
            layouts = data.layouts;
            // Build an item dictionary that includes its colours
            items = {};
            for (var i = 0; i < itemArray.length; i++) {
                console.log(itemArray[i].pk + " " + itemArray[i].fields);
                if (!itemArray[i].fields.colour){
                    itemArray[i].fields.colour = 0;
                }
                var colour = lookupColour(itemArray[i].fields.colour, colours);
                itemArray[i].fields.forecolour = colour.fore_colour;
                itemArray[i].fields.backcolour = colour.back_colour;
                items[itemArray[i].pk] = itemArray[i].fields;
            }
        }
    }

    function applyLayout(id){
        var col;
        var item;
        var layout = JSON.parse(layouts[id]);
        $('.item-button').hide();
        Object.keys(layout).forEach(function (value) {
            col = value[5];
            if (col === '0') {
                $(value).text(layout[value]).show();
            } else {
                item = items[layout[value]];
                $(value).prop('value', item.description).show().css('background-color', item.backcolour).prop('item', item);
            }
        });

    }

    function loadPeople(){
        $.ajax({
            type: 'GET',
            url: urls.adults,
            timeout: ajaxTimeout,
            success: function (response) {
                console.log('saving people');
                localStorage.setItem('people', JSON.stringify(response));
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log('Error loadPeople ' + textStatus);
            }
        });
    }

    function lookupColour(id, colours) {
        var i;
        for (i = 0; i < colours.length; i++) {
            if (colours[i].pk === id) {
                return colours[i].fields;
            }
        }
        return colours[0].fields;
    }

    function lookupItem(id) {
        return items[id];
        // var i;
        // for (i = 0; i < items.length; i++) {
        //     if (items[i].pk === id) {
        //         return items[i].fields;
        //     }
        // }
    }

    function createTable(receipt) {
        var tableBody = document.createElement('tbody');
        var row;
        var cell;
        var button;
        payClass.hide();
        exitClass.hide();
        while (receiptArea.firstChild) {
            receiptArea.removeChild(receiptArea.firstChild);
        }
        total = 0;
        if (receipt.length > 0) {
           payClass.show();
            receipt.forEach(function (item) {
                row = document.createElement('tr');
                cell = document.createElement('td');
                cell.className = "description";
                cell.appendChild(document.createTextNode(item.description));
                row.appendChild(cell);
                cell = document.createElement('td');
                cell.className = "price";
                cell.appendChild(document.createTextNode(item.sale_price));
                row.appendChild(cell);
                cell = document.createElement('td');
                cell.className = "del-button";
                button = document.createElement("button");
                button.className ="btn-danger";
                button.id = item.lineId;
                button.innerHTML = "X";
                button.addEventListener("click", function (event) {
                    pos.itemRemove(event.currentTarget.id);
                }, false);
                cell.appendChild(button);
                row.appendChild(cell);
                tableBody.appendChild(row);
                total += item.price;
            });
            receiptArea.appendChild(tableBody);
        } else {
            exitClass.show();
        }
        formattedTotal = '£ ' + Number(total/100).toFixed(2);
        $('#total-area').text("Total : " + formattedTotal);
    }


    function setOnline(){
        online = true;
        $('#idOnline').text('Online');
        $('#menuTransactions').show();
    }

    function setOffline(){
        online = false;
        $('#idOnline').text('Offline');
        $('#menuTransactions').hide();
    }
    

    function initPing(timeout, url, term) {
        // Initialise a regular ping message
        pingTimeout = timeout;
        pingUrl = url;
        terminal = term;
        ping();
    }

    function stopPing () {
        clearTimeout(pingTimer);
    }

    function startPing() {
        pingTimer = setTimeout(ping, pingTimeout);
    }

    function ping() {
        // post a message to the server with terminal number
        $.ajax({
            type: "POST",
            url: urls.ping,
            data: 'terminal=' + terminal,
            timeout: pingTimeout,
            success: function (data, status, xhr) {
                $('#idOfflineMessage').hide();
                $('#idOnlineMessage').show();
                setOnline();
                if (data === 'OK') {
                    if (getContents().length > 0) {
                        recoverTransactions();
                    }
                    startPing();
                }else if (data.slice(0, 7) === 'Restart') {
                    window.location.replace(data.slice(8));
                }else{
                    pos.startApp();
                }
            },
            error: function (data, status, xhr) {
                setOffline();
                startPing();
            }
        });
    }
    return pos;
})();