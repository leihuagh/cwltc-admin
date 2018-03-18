var PosCode;
PosCode = (function () {
    "use strict";

    var Pos = {};

    // DOM objects
    var receiptArea = document.getElementById('id_receipt');
    var totalArea = document.getElementById('id_total');
    var receiptTable = document.getElementById('id_table');
    var peopleTable = document.getElementById('peopleTable');
    var payButton = document.getElementById('id_pay');
    var exitButton = document.getElementById('id_exit');
    var cancelButton = document.getElementById('id_cancel');

    var items;
    var receipt;
    var total;
    var line;

    // Django context variables
    var itemsUrl, postUrl, exitUrl;
    var isAttended = false;
    var personId;
    var person;
    var personName;
    var personList;

    /* Public methods*/
    Pos.init = function (items_url, post_url, exit_url, is_attended, person_id, person_name) {
        itemsUrl = items_url;
        postUrl = post_url;
        exitUrl = exit_url;
        isAttended = is_attended;
        personId = person_id;
        personName = person_name;
        loadItems();
        newReceipt();
    };

    Pos.itemAdd = function (id) {
        // Add item to receipt array
        var obj = lookup(id);
        var item = {};
        item.id = id;
        item.lineId = 'line_' + line;
        line++;
        item.description = obj.description;
        item.sale_price = obj.sale_price;
        item.cost_price = obj.cost_price;
        receipt.push(item);
        createTable(receipt);
    };

    Pos.newReceipt = function () {
        newReceipt();
    };

    Pos.itemRemove = function (target) {
        var index;
        for (index = 0; index < receipt.length; ++index) {
            if (receipt[index].lineId === target) {
                receipt.splice(index, 1);
                createTable(receipt);
                return;
            }
        }
    };


    Pos.pay = function () {
        personList = [];
        var myTotal = '£' + Number(total).toFixed(2);
        if (isAttended) {
            $('#attended_total').text(myTotal);
            $('#attended_modal').modal('show');
        } else {
            $('#member_total').text(myTotal);
            $('#member_modal').modal('show');
        }
        $('#memberSearch').val('');
        $('.typeahead').typeahead('val', '');
    };

    Pos.exitPos = function () {
        window.location.replace(exitUrl);
    };

    Pos.selectMember = function () {
        console.log('selected');
    };

    Pos.cash = function () {
        personList = [];
        sendTransaction('cash');
    };

    Pos.chargeSingleMember = function () {
        // charge to single logged on member
        personList = [{'id': personId, 'name': personName, 'amount': Math.floor(total*100)}];
        sendTransaction('account');
    };

    Pos.chargeMultipleMembers = function () {
        // charge to single logged on member
        sendTransaction('account');
    };

    Pos.account = function () {
        // Select first member in attended mode
        personList = [];
        $('#addMemberTypeahead').show();
        $('#payButtons').hide();
        $('#select_modal').modal('show');
    };

    Pos.split = function () {
        // initiate a split across members
        personList = [{'id': personId, 'name': personName}];
        showSplit();
        $('#addMemberTypeahead').hide();
        $('#paybuttons').show();
        $('#select_modal').modal('show');
    };

    Pos.addMember = function() {
        // add member button on split sale modal
        $('#addMemberTypeahead').show();
        $('#payButtons').hide();
        $('#memberSearch').val('').focus();
        $('.typeahead').typeahead('val', '');
        $('#select_modal').modal('show');
    };

    Pos.selectedPerson = function (p) {
        // user selected a person through the type ahead
        person = p;
        personList.push({'id': p.id, 'name': p.value});
        showSplit();
        $('#addMemberTypeahead').hide();
        $('#payButtons').show();
        $('#select_modal').modal('show');
    };

    Pos.back1 = function() {
        if (isAttended) {
            $('#select_modal').modal('hide');
        } else {
            $('#addMemberTypeahead').hide();
            $('#payButtons').show();
            $('#select_modal').modal('show');
        }

    };

    function showSplit() {
        var row;
        var cell;
        var tableBody = document.createElement('tbody');
        while (peopleTable.firstChild) {
            peopleTable.removeChild(peopleTable.firstChild);
        }
        var totalPence = total * 100;
        var splitPence = Math.floor(totalPence/personList.length);
        var firstPence = splitPence;
        var splitTotal = splitPence * personList.length;
        if (splitTotal !== totalPence) {
            firstPence += (totalPence - splitTotal);
        }
        for (var i = 0; i < personList.length; i++) {
            if (i === 0) {
                personList[i].amount = firstPence;
            } else {
                personList[i].amount = splitPence;
            }
            row = document.createElement('tr');
            cell = document.createElement('td');
            cell.className = "description";
            cell.appendChild(document.createTextNode(personList[i].name));
            row.appendChild(cell);
            cell = document.createElement('td');
            cell.className = "price";
            cell.appendChild(document.createTextNode((personList[i].amount/100).toFixed(2)));
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
        peopleTable.appendChild(tableBody);
        $('#add_member').hide();
        $('#select_modal').modal('show');
    }

    function sendTransaction(payType) {
        var payObj = {'pay_type': payType, 'people': personList};
        receipt.push(payObj);
        var data = JSON.stringify(receipt);
        $.post(postUrl, data, function(result){
            window.location.replace(result);
        });
    }


    Pos.resume = function () {
        $('#pay_modal').modal('hide');
    };

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
                console.log("items loaded");
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
        payButton.style.visibility = "hidden";
        cancelButton.style.visibility = "hidden";
        exitButton.style.visibility = "hidden";
        while (receiptTable.firstChild) {
            receiptTable.removeChild(receiptTable.firstChild);
        }
        total = 0;
        if (receipt.length > 0) {
            payButton.style.visibility = "visible";
            cancelButton.style.visibility = "visible";
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
                button.id = item.lineId;
                button.innerHTML = "X";
                button.addEventListener("click", function (event) {
                    console.log(event.currentTarget);
                    Pos.itemRemove(event.currentTarget.id);
                }, false);
                cell.appendChild(button);
                row.appendChild(cell);
                tableBody.appendChild(row);
                total += Number(item.sale_price);
            });
            receiptTable.appendChild(tableBody);
        } else {
            exitButton.style.visibility = "visible";
        }
        totalArea.innerHTML = "<h3> Total :" + Number(total).toFixed(2) + "<h3>";
    }
    return Pos;
})();