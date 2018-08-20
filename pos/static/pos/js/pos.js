
// Version 3 Fully support offline working
var posCode = (function () {
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
    pos.init = function (items_url, post_url, exit_url, is_attended, layout_id, csrf_token, timing) {
        itemsUrl = items_url;
        postUrl = post_url;
        exitUrl = exit_url;
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
        //localStorage.clear();

        loadItems();

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
        stamp = new Date().getTime();
        var payObj = {
            'pay_type': payType,
            'people': personList,
            'total': total,
            'stamp': stamp,
            'layout_id': layoutId
        };
        receipt.push(payObj);
        var transaction = JSON.stringify(receipt);

        $('#save_message').text('Saving transaction to server ...');
        $('#save_error').text(' ');
        $('#save-footer').hide();
        $('#save_modal').modal('show');
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
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log ('Error {xhr} {textStatus}')
                saveTransaction(transaction, stamp);
            }
        });
    }


    function saveTransaction(trans, stamp){
        // Save trans in local storage
        var key = 'Trans:{stamp}';
        localStorage.setItem(key, trans);
        var index = localStorage.getItem('index');
        if (!index){
            index = [];
        }
        index.push(stamp);
    }


    function removeTransaction(stamp){
        // Save trans in local storage
        var key = 'Trans:{stamp}';
        localStorage.setItem(key, trans);
        var index = localStorage.getItem('index');
        if (!index){
            index = [];
        }
        index.push(stamp);
    }

    function unsaveTransaction(stamp){
        var transaction = localStorage.getItem(stamp);
        $.ajax({
            type: "POST",
            url: postUrl,
            data: transaction,
            dataType: 'text',
            timeout: 10000,
            success: function (response) {
                if (response === 'saved') {
                    console.log('Recovery {stamp} written to server');
                    removeTransaction(stamp);
                }else{
                    console.log('Recovery server error {stamp}');
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                console.log ('Recovery error {xhr} {textStatus} {stamp}');
            }
        });
    }

    function newReceipt() {
        receipt = [];
        line = 0;
        createTable(receipt);
    }

    // function loadItems() {
    //     // AJAX request to download items with description & price
    //     var xhttp = new XMLHttpRequest();
    //     xhttp.onreadystatechange = function () {
    //         if (this.readyState === 4 && this.status === 200) {
    //             var jsonData = this.responseText;
    //             items = JSON.parse(JSON.parse(this.responseText));
    //             $('.flex-left').show();
    //             $('.flex-right').show();
    //         }
    //     };
    //     xhttp.open("GET", itemsUrl, true);
    //     xhttp.send();
    // }

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
                    console.log('saving items')
                    localStorage.setItem('items', response);
                    items = JSON.parse(response);
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
    return pos;
})();