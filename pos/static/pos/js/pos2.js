
// Version 2 Handle currency as integer always
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
    var isAttended = false;
    var personId;
    var person;
    var personName;
    var personList;

    var timer;

    /* Public methods*/
    pos.init = function (items_url, post_url, exit_url, is_attended, person_id, person_name, csrf_token, timing) {
        itemsUrl = items_url;
        postUrl = post_url;
        exitUrl = exit_url;
        isAttended = is_attended;
        personId = person_id;
        personName = person_name;
        timer = timing;
        payClass.hide();
        exitClass.hide();
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader('X-CSRFToken', csrf_token);
            }
        });
        loadItems();
        $(".posbutton").on('touchstart', function(event) {
            pos.itemAdd(Number(event.currentTarget.id));
            event.currentTarget.classList.add('posbutton-down');
            timing.restartTimer();
            event.preventDefault();
        });
        // Click event for testing
        $(".posbutton").on('click', function(event) {
            pos.itemAdd(Number(event.currentTarget.id));
        });
        $(".posbutton").on('touchend', function(event) {
            event.currentTarget.classList.remove('posbutton-down');
        });
        newReceipt();
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

    pos.newReceipt = function () {
        newReceipt();
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

    pos.exitPos = function () {
        window.location.replace(exitUrl);
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
        var payObj = {'pay_type': payType, 'people': personList, 'total': total};
        receipt.push(payObj);
        var data = JSON.stringify(receipt);
        // $.post(postUrl, data, function(result){
        //     window.location.replace(result);
        // });
        $('#save_message').text('Saving transaction to server ...');
        $('#save_error').text(' ');
        $('#save-footer').hide();
        $('#save_modal').modal('show');
        var fatal = false;
        var message = '';
        $.ajax({
            type: "POST",
            url: postUrl,
            data: data,
            dataType: 'text',
            tryCount: 0,
            retryLimit: 3,
            timeout: 10000,
            success: function (target) {
                if (target.includes('<')) {
                    console.log('bad url received');
                }else if (target === 'Error'){
                    $('#save_message').text('Sorry, the server could not save the transaction.');
                    $('#save_error').text('Please try to pay again or record it on paper.');
                    $('#save-footer').show();
                    receipt.pop(payObj);
                }else{
                    window.location.replace(target);
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                if (textStatus === 'timeout') {
                    this.tryCount++;
                    if (this.tryCount < this.retryLimit) {
                        $('#save_error').text('No response from server. Retrying ' + this.tryCount.toString());
                        $.ajax(this);
                        return;
                    }
                    fatal = true;
                    message = 'Timeout';
                }
                if (xhr.status === 500) {
                    fatal = true;
                    message = 'Server error';
                }
                if (fatal) {
                    console.log('Bad server response');
                    $('#save_message').text(message + ' Sorry, the transaction could not be saved.');
                    $('#save_error').text('Please try to pay again or record it on paper.');
                    $('#save-footer').show();
                    receipt.pop(payObj);
                    timer.startTimer(60000, exitUrl);
                }
            }
        });
    }

    function newReceipt() {
        receipt = [];
        line = 0;
        createTable(receipt);
    }

    function loadItems() {
        // AJAX request to download items with description & price
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            if (this.readyState === 4 && this.status === 200) {
                var jsonData = this.responseText;
                items = JSON.parse(JSON.parse(this.responseText));
                $('.flex-left').show();
                $('.flex-right').show();
            }
        };
        xhttp.open("GET", itemsUrl, true);
        xhttp.send();
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
        // payButton.style.visibility = "hidden";
        // cancelButton.style.visibility = "hidden";
        // exitButton.style.visibility = "hidden";
        while (receiptArea.firstChild) {
            receiptArea.removeChild(receiptArea.firstChild);
        }
        total = 0;
        if (receipt.length > 0) {
            // payButton.style.visibility = "visible";
            // cancelButton.style.visibility = "visible";
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
            // exitButton.style.visibility = "visible";
            exitClass.show();
        }
        formattedTotal = '£ ' + Number(total/100).toFixed(2);
        totalArea.innerHTML = "Total : " + formattedTotal;
    }
    return pos;
})();