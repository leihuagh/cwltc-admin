// Version 3 Fully support offline working
var posCode = (function (){
    "use strict";

    var pos = {};

    // DOM objects
    var totalArea = document.getElementById('total-area');
    var receiptArea = document.getElementById('receipt-area');
    var peopleTable = document.getElementById('peopleTable');
    var payButton = document.getElementById('id_pay');
    var exitButton = document.getElementById('id_exit');
    var cancelButton = document.getElementById('id_cancel');
    var payClass = $('.buttons-active');
    var exitClass = $('.button-exit');

    var items;
    var receipt;
    var total;
    var formattedTotal;
    var line;
    var online = false;

    // Django context variables
    var itemsUrl, postUrl, exitUrl;
    var layoutId;
    var isAttended = false;

    var personId;
    var person;
    var personName;
    var personList;

    var timer;

    /* Public methods*/
    pos.init = function (items_url, post_url, ping_url, is_attended, layout_id, csrf_token, terminal, timeout, timing) {
        itemsUrl = items_url;
        postUrl = post_url;
        pingUrl = ping_url;
        isAttended = is_attended;
        layoutId = layout_id;
        timer = timing;
        payClass.hide();
        exitClass.hide();
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader('X-CSRFToken', csrf_token);
            }
        });
        localStorage.clear();
        initPing(timeout, ping_url, terminal);
        loadItems();
        loadPeople();

        $(".posbutton").on('touchstart', function(event) {
            pos.itemAdd(Number(event.currentTarget.id));
            event.currentTarget.classList.add('posbutton-down');
            timing.restartTimer();
            event.preventDefault();
        });

        // Click event for testing in browser
        $(".posbutton").on('click', function(event) {
            pos.itemAdd(Number(event.currentTarget.id));
        });
        $(".posbutton").on('touchend', function(event) {
            event.currentTarget.classList.remove('posbutton-down');
        });
        newReceipt();
    };

    pos.showPage = function(pageId){
        $('#idPageStart').hide();
        $('#idPageGetUser').hide();
        $('#idPageGetPassword').hide();
        $('#idPagePos').hide();
        if (pageId === '#idPagePos') {
          $('#idLogoBanner').hide();
        }else{
          $('#idLogoBanner').show();
        }
        if (pageId === '#idPageStart') {
            startPing();
        }else{
            stopPing();
        }
        $(pageId).show();
    };

    pos.startApp = function (){
        pos.showPage('#idPageStart');
    };

    pos.getUser = function(){
        pos.showPage('#idPageGetUser');
        $('#idNameInput').val('').focus();
    };

    pos.gotUser = function(person) {
        personId = person.id;
        personName = person.value;
        $('.typeahead').typeahead('val', '');
        pos.showPage('#idPageGetPassword');
        $('#idPasswordName').text(personName);
        $('#idPersonId').val(personId); // hidden field on form
        $('#idPinInput').val('').focus();
        $('#idPasswordInput').val('');
    };

    pos.submitPassword = function() {
        $.ajax({
            type: 'GET',
            url: '/pos/ajax/password/',
            data: $('#idPasswordForm').serialize(),
            timeout: 10000,
            success: function (response) {
                if (response === 'pass'){
                  pos.newReceipt();
                }else{
                  console.log(response);
                  pos.startApp();
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                if (textStatus === 'timeout') {
                  console.log('timeout');
                }
            }
        });
    };

    pos.newReceipt = function(){
        newReceipt();
        $('#id_PosName').val(personName);
        pos.showPage('#idPagePos');
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

    // pos.newReceipt = function () {
    //     newReceipt();
    // };

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

    pos.exitPos = function () {
        pos.startApp();
    };

    pos.selectMember = function () {
        console.log('selected');
    };

    pos.cash = function () {
        personList = [];
        sendTransaction('cash');
    };

    pos.commitSingle = function () {
        // charge to single logged on member
        personList = [{'id': personId, 'name': personName, 'amount': total}];
        sendTransaction('account');
    };

    pos.commit = function () {
        // charge to list of members
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
        $('#select_modal').modal('hide');
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
        $('#pay_modal').modal('hide');
    };

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
        $('#select_modal').modal('show');
    }

    function sendTransaction(payType) {
        // post the transaction to the server
        // the response is the next screen to show
        timer.stopTimer();
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

        // $('#save_message').text('Saving transaction to server ...');
        // $('#save_error').text(' ');
        // $('#save-footer').hide();
        // $('#save_modal').modal('show');
        var fatal = false;
        var message = '';
        $.ajax({
            type: "POST",
            url: postUrl,
            data: transaction,
            dataType: 'text',
            tryCount: 0,
            retryLimit: 1,
            timeout: 10000,
            success: function (response) {
                if (response === 'saved') {
                    console.log('Transaction saved');
                    // TODO last transaction
                    pos.startApp();
                }else{
                    console.log('Transaction error - save locally');
                    saveTransaction(transaction, stamp);
                    pos.startApp();
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log ('Error {xhr} {textStatus}');
                saveTransaction(transaction, stamp);
                pos.startApp();
            }
        });
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
                url: postUrl,
                data: localStorage.getItem(contents[0]),
                dataType: 'text',
                timeout: 10000,
                success: function(response){
                    console.log(response);
                    if (response.slice(0, 5) === 'saved'){
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
                    console.log('Error ' + xhr + ' ' + textStatus);
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
        if (savedItems) {
            console.log('Using items from storage');
            items = JSON.parse(savedItems);
            $('.flex-left').show();
            $('.flex-right').show();

        }else{
            console.log('Start get items');
            $.ajax({
                type: 'GET',
                url: itemsUrl,
                timeout: 10000,
                success: function (response) {
                    console.log('saving items');
                    localStorage.setItem('items', response);
                    items = JSON.parse(response);
                    var test = localStorage.getItem('items');
                    alert(test.length.toString() + ' items loaded');
                    $('.flex-left').show();
                    $('.flex-right').show();
                },
                error: function (xhr, textStatus, errorThrown) {
                    if (textStatus === 'timeout') {
                        console.log('timeout');
                    }
                }
            });
        }
    }

    function loadPeople(){
        $.ajax({
            type: 'GET',
            url: '/ajax/adults',
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
        totalArea.innerHTML = "Total : " + formattedTotal;
    }


    function setOnline(){
        online = true;
        $('#idOnline').text('Online');
    }

    function setOffline(){
        online = false;
        $('#idOnline').text('Offline');
    }

    var pingTimer;
    var pingTimeout = "";
    var pingUrl = "";
    var terminal = 0;

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
            url: pingUrl,
            data: 'terminal=' + terminal,
            timeout: pingTimeout,
            success: function (data, status, xhr) {
                $('#idOfflineMessage').hide();
                $('#idOnlineMessage').show();
                setOnline();
                if (data === 'OK') {
                    if (getContents().length > 0){
                        recoverTransactions();
                    }
                    startPing();
                }else{
                    pos.startApp();
                }
            },
            error: function (data, status, xhr) {
                $('#idOfflineMessage').show().text('Sorry, the server is temporarily available. Please try later');
                $('#idOnlineMessage').hide();
                setOffline();
                startPing();
            }
        });
    }




    return pos;
})();