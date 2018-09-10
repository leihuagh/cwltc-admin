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
    var timeout = 120000;

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
        loadItems();
        loadPeople();
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

        newReceipt();
    };

    pos.touch = function(event, action) {
        handleTouch(event, action);
    };

    pos.touchEnd = function(event, action) {
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
                pos.itemAdd(Number(event.currentTarget.id));
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
                $('#passwordPin').focus();
                break;
            case '#pageResetPin':
                $('#resetForm').show();
                $('#resetDone').show();
                $('#resetPostCode').val('').focus();
                $('#resetPhone').val('');
                $('#resetActionArea').hide();
                $('#resetError').text('');
        }
    };

    pos.startApp = function(){
        isAttended = false;
        if (personId) {
            pos.showMenu();
        }else{
            pos.showPage('#pageStart');
        }
    };

    pos.attended = function() {
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
            timeout: 2000,
            success: function (response) {
                if (response === 'OK'){
                    $('#resetForm').hide();
                    $('#resetError').text('');
                    $('#resetActionArea').show();
                    $('#resetPin').val('').focus();
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
            timeout: 2000,
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
        var formData = $('#idPasswordForm').serialize();
        var query = parseQuery(formData);
        if (online){
            $.ajax({
                type: 'POST',
                url: urls.password,
                data: formData,
                timeout: 2000,
                success: function (response) {
                    if (response === 'pass'){
                        setOnline();
                        if (query.pin){
                            localStorage.setItem('id:' + query.person_id, btoa(query.pin));
                        }
                        pos.showMenu();
                    } else {
                        console.log(response);
                        pos.startApp();
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

    pos.transactions = function() {
        clearTimeout(timer);
        if (personId === -1){
            window.location.href = '/pos/transactions/comp/' + '?pos=true';
        } else {
            window.location.href = '/pos/transactions/person/' + personId + '?pos=true';
        }
    };


    function testOfflinePin(query){
        // test submitted query against stored offline pin
        // if its present and matches start pos
        // if present and wrong -> error
        // if not present, start pos
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

    pos.newReceipt = function(){
        newReceipt();
        $('#id_PosName').text(personName);
        pos.showPage('#pagePos');
    };

    pos.itemAdd = function (id) {
        // Add item to receipt array
        var obj = lookup(id);
        var item = {};
        item.id = id;
        item.lineId = 'line_' + line;
        line++;
        item.description = obj.description;
        item.sale_price = obj.sale_price;
        item.cost_price = obj.cost_price;
        item.price = Math.fround(parseFloat(item.sale_price)*100);
        receipt.push(item);
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
        var fatal = false;
        var message = '';
        $.ajax({
            type: "POST",
            url: urls.sendTransaction,
            data: transaction,
            dataType: 'text',
            tryCount: 0,
            retryLimit: 1,
            timeout: 10000,
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
                timeout: 10000,
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

    function loadItems() {
        var savedItems = localStorage.getItem('items');
        console.log('Start get items');
        $.ajax({
            type: 'GET',
            url: urls.items,
            timeout: 10000,
            success: function (response) {
                console.log('Saving items');
                localStorage.setItem('items', response);
                items = JSON.parse(response);
                $('.flex-left').show();
                $('.flex-right').show();
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log('Error reading items ' + textStatus);
                if (savedItems) {
                    alert('Using items from storage');
                    items = JSON.parse(savedItems);
                    $('.flex-left').show();
                    $('.flex-right').show();
                } else {
                    alert('Cannot access items');
                }
            }
        });
    }

    function loadPeople(){
        $.ajax({
            type: 'GET',
            url: urls.adults,
            timeout: 10000,
            success: function (response) {
                console.log('saving people');
                localStorage.setItem('people', JSON.stringify(response));
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log('Error loadPeople ' + textStatus);
            }
        });
    }

    var lookup = function (id) {
        var index;
        for (index = 0; index < items.length; index++) {
            if (items[index].pk === id) {
                return items[index].fields;
            }
        }
        return false;
    };

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
                // $('#idOfflineMessage').show().text('Sorry, the server is temporarily available. Please try later');
                // $('#idOnlineMessage').hide();
                setOffline();
                startPing();
            }
        });
    }




    return pos;
})();