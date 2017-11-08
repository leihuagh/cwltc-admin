function allowDrop(ev) {
    ev.preventDefault();
}

function drag(ev) {
    ev.dataTransfer.setData("text/plain", ev.target.id);
}

function dragEnd(ev) {
    ev.target.style.border = "none";
}

function drop(ev) {
    ev.preventDefault();
    var id = ev.dataTransfer.getData("text/plain");
    var from_button = document.getElementById(id);
    var x = id.substring(0, 2);
    if (x === 'id') {

        if (ev.target.id === 'bin'){
            // drag button to bin
            var item_id='item:'+from_button.value;
            var item_button = document.getElementById(item_id);
            enable(item_button);
            from_button.value = "";
            disable(from_button);
        }else {
            // drag button to button if different button and empty
            if (ev.target.id !== id && ev.target.value ===""){
                ev.target.value = from_button.value;
                enable(ev.target);
                from_button.value = "";
                disable(from_button);
            }
        }
    }else{
        // drag item to button
        ev.target.value = id.slice(5);
        disable(from_button);
        enable(ev.target);
    }
}

function enable(button){
    button.classList.remove('btn-default');
    button.classList.add('btn-success');
    button.draggable=true;
}

function disable(button){
    button.classList.remove('btn-success');
    button.classList.add('btn-default');
    button.draggable=false;
}
