$.fn.exists = function () {
    return this.length !== 0;
}

function sortResults(data) {
    return data.sort(function (a, b) {
        return a.circuit - b.circuit;
    });
}

function SyncDevice(msg) {
    //todo: add name as parameter
    var name = "";
    var circuit = msg.circuit;
    var dev_type = msg.dev;
    var value = msg.value;
    var unit = "";
    var ns = "unipi_" + dev_type + "_" + circuit;

    if (dev_type == 'ai') {
        name = "Analog input " + circuit;
        value = msg.value.toFixed(3);
        unit = "V";
    }
    else if (dev_type == 'ao') {
        name = "Analog output " + circuit;
        unit = "V";
        value = msg.value.toFixed(1);
    }
    else if (dev_type == 'relay') {
        name = "Relay " + circuit;
    }
    else if (dev_type == 'input') {
        name = "Input " + circuit;
    }
    else if (dev_type == 'temp') {
        name = "Sensor " + circuit;
        if (msg.value == null) {
            value = "null";
        }
        else {
            value = msg.value.toFixed(1);
            unit = "°C";
        }
    }
    //todo: unite names of device types here and in evok
    if (!$('#' + ns + '_li').length > 0) {
        li = document.createElement("li");
        li.id = ns + "_li";

        div = document.createElement("div");
        div.className = "ui-field-contain";

        if (dev_type == 'relay') {
            main_el = document.createElement("select");
            main_el.className = "ui-li-aside";
            var option_on = document.createElement("option");
            option_on.value = 1;
            option_on.innerText = "On";
            var option_off = document.createElement("option");
            option_off.value = 0;
            option_off.innerText = "Off";
            main_el.add(option_off);
            main_el.add(option_on);
        }
        else if (dev_type == "ao") {
            main_el = document.createElement("input");
            main_el.className = "out";
            main_el.min = 0;
            main_el.max = 10;
            main_el.step = 0.1;
        }
        else if (dev_type == "temp") {
            main_el = document.createElement("h1");
            main_el.innerText = value + unit;
            main_el.className = "ui-li-aside";
        }
        else {
            main_el = document.createElement("h1");
            var state = "Off";
            if (value == 1) {
                state = "On;"
            }
            main_el.innerText = state + unit;
            main_el.className = "ui-li-aside";
        }

        main_el.id = ns + "_value";

        //create label
        label = document.createElement("label");
        label.id = ns + "_label";
        label.setAttribute("for", main_el.id);
        label.innerText = name;

        //create structure
        div.appendChild(label);
        div.appendChild(main_el);
        li.appendChild(div);

        //and append it to the html
        if (dev_type == 'ai') {
            var divider = document.getElementById("unipi_temp_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (dev_type == 'ao') {
            $('#outputs_list').append(li);
            $('#' + main_el.id).slider();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("slidestop", function (event, ui) {
                do_action('ao/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (dev_type == 'relay') {
            var divider = document.getElementById("unipi_ao_divider");
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                do_action('relay/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (dev_type == 'input') {
            var divider = document.getElementById("unipi_ai_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (dev_type == 'temp') {
            $('#inputs_list').append(li);
            $('#inputs_list').listview('refresh');
        }
    }
    else {
        //get elements
        var main_el = document.getElementById(ns + "_value");
        var label = document.getElementById(ns + "_label");
        //and update values
        label.innerText = name;
        //outputs
        if (dev_type == 'relay') {
            //TODO: remove re-binding when/if more events for flispwitch are available to prevent looping
            //unbind to prevent looping
            $('#' + main_el.id).unbind("change");
            $("#" + ns + "_value").val(value).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                do_action('relay/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (dev_type == 'ao') {
            $("#" + ns + "_value").val(value).slider("refresh");
        }
        //inputs
        else if (dev_type == 'input') {
            var state = "Off";
            if (value == 1) {
                state = "On";
            }
            main_el.innerHTML = state;
        }
        else {
            main_el.innerHTML = value + unit;
        }
    }
}

function update_values() {
    $.ajax({
        url: 'rest/all/',
        dataType: 'json',
        success: function (data) {
            data = sortResults(data);
            $.each(data, function (name, msg) {
                SyncDevice(msg);
            });
        },
        error: function (data) {
        }
    });
}


var ws = null;
var use_polling = false;
var timer = null;


function WebSocketRegister() {
    if ("WebSocket" in window) {
        if (ws) {
            return
        }
        var loc = window.location;
        uri = ((loc.protocol === "https:") ? "wss://" : "ws://") + loc.hostname +
            (((loc.port != 80) && (loc.port != 443)) ? ":" + loc.port : "");

        ws = new WebSocket(uri + "/ws");
        //var wnd = null;

        if (!ws) {
            setTimeout(WebSocketRegister, 1000);
            return;
        }

        window.onbeforeunload = function () {
            ws.onclose = function () {
            }; // disable onclose handler first
            ws.close()
        };

        ws.onopen = function () {
            update_values();
        };

        ws.onmessage = function (evt) {
            var received_msg = evt.data;
            var msg = JSON.parse(evt.data);
            SyncDevice(msg);
        };

        ws.onclose = function () {
            //alert("Connection is closed...");
            setTimeout(WebSocketRegister, 1000);
            ws = null;
        };
    }
    else {
        //alert("WebSocket NOT supported by your Browser!");
        use_polling = true;
    }
}

function do_action(action, params) {
    $.ajax({
        url: '/rest/' + action,
        //dataType:'json',
        type: 'POST',
        data: params || null,
        //crossDomain: false,
        success: function (data) {
        },
        error: function (data) {
        }
    });
}