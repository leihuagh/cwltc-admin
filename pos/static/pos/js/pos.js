var PosCode = (function () {
    "use strict";

    var Pos = {};

    /* DOM objects */
    var receiptArea = document.getElementById('id_receipt');
    var totalArea = document.getElementById('id_total');
    var table = document.getElementById('id_table');
    var payButton = document.getElementById('id_pay');
    var exitButton = document.getElementById('id_exit');
    var cancelButton = document.getElementById('id_cancel');

    /* Django context variables */
    var itemsUrl, postUrl, exitUrl;

    var items;
    var receipt;
    var line;

    /* Public functions */
    Pos.init = function(items, post, exit) {
        console.log("init");
        itemsUrl = items;
        postUrl = post;
        exitUrl = exit;

        loadItems();
        newReceipt();
    };

    Pos.itemAdd = function(id) {
        // Add item to receipt array
        var obj = lookup(id);
        var item = {};
        item.id = id;
        item.lineId = 'line_' + line;
        line++;
        item.description = obj.description;
        item.sale_price = obj.sale_price;
        receipt.push(item);
        createTable(receipt);
    };

    Pos.newReceipt = function() {
        newReceipt();
    };

    Pos.pay = function() {
        $('#id_total1').text($('#id_total').text());
        $('#id_total2').text($('#id_total').text());
        $('#pay_modal').modal('show');
    };

    Pos.exitPos = function() {
        window.location.replace(exitUrl);
    };

    Pos.cash = function() {
        console.log('cash');
        Pos.exitPos();
    };

    Pos.account = function() {
        console.log('account');
        Pos.exitPos();
    };

    Pos.back = function() {
        $('#pay_modal').modal('hide');
    };

    function newReceipt() {
        receipt = [];
        line = 0;
        createTable(receipt);
    }

    var loadItems = function () {
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
    };

    var lookup = function (id) {
        var index;
        for (index = 0; index < items.length; ++index) {
            if (items[index].pk === id) {
                return items[index].fields;
            }
        }
        return false;
    };

    function createTable(receipt) {
        var tableBody = document.createElement('tbody');
        var total = 0;
        var row;
        var cell;
        var button;
        payButton.style.visibility = "hidden";
        cancelButton.style.visibility = "hidden";
        exitButton.style.visibility = "hidden";
        while (table.firstChild) {
            table.removeChild(table.firstChild);
        }
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
                button.addEventListener("click", function(){Pos.itemRemove(button.id);}, false);
                cell.appendChild(button);
                row.appendChild(cell);
                tableBody.appendChild(row);
                total += Number(item.sale_price);
            });
            table.appendChild(tableBody);
        } else {
            exitButton.style.visibility = "visible";
        }
        totalArea.innerHTML = "<h3> Total :" + Number(total).toFixed(2) + "<h3>";
    }

    Pos.itemRemove = function (target) {
        var index;
        for (index = 0; index < receipt.length; ++index) {
            if (receipt[index].lineId === target) {
                receipt.splice(index, 1);
                createTable(receipt);
                return;
            }
        }
    }

    return Pos;
})();