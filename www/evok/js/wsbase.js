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
    var device = msg.dev;
    var typ = msg.typ;
    var value = msg.value;
    var unit = "";
    var ns = "unipi_" + device + "_" + circuit;

    if (device == 'ai') {
        name = "Analog input " + circuit;
        value = msg.value.toFixed(3);
        unit = "V";
    }
    else if (device == 'ao') {
        name = "Analog output " + circuit;
        unit = "V";
        value = msg.value.toFixed(1);
    }
    else if (device == 'relay') {
        name = "Relay " + circuit;
    }
    else if (device == 'input') {
        name = "Input " + circuit;
        counter = msg.counter;
    }
    else if (device == 'temp' || device == '1wdevice') {
        name = "Sensor " + typ + " - " + circuit;
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

        if (device == 'relay') {
            main_el = document.createElement("select");
            main_el.className = "ui-li-aside";
            var option_on = document.createElement("option");
            option_on.value = 1;
            option_on.textContent = "On";
            var option_off = document.createElement("option");
            option_off.value = 0;
            option_off.textContent = "Off";
            main_el.add(option_off);
            main_el.add(option_on);
        }
        else if (device == "ao") {
            main_el = document.createElement("input");
            main_el.className = "out";
            main_el.min = 0;
            main_el.max = 10;
            main_el.step = 0.1;
        }
        else if (device == "temp" || device == "1wdevice") {
            main_el = document.createElement("h1");
            main_el.textContent = value + unit;
            main_el.className = "ui-li-aside";
        }
        else if (device == "input") {
            cnt_el = document.createElement("h1");
            cnt_el.textContent = counter;
            cnt_el.className = "ui-li-aside";
            cnt_el.style = "right: 7em";
            cnt_el.id = ns + "_counter";

            cfg_el = document.createElement("a");
            cfg_el.className = "ui-icon-gear ui-btn-icon-notext ui-corner-all";
            cfg_el.href = "#popupBasic"; 
            cfg_el.setAttribute("data-rel","popup"); 
            cfg_el.setAttribute("data-position-to","window");
            cfg_el.setAttribute("data-transition","pop"); 
            cfg_el.id = ns + "_cfg";

            main_el = document.createElement("h1");
            var state = "Off";
            if (value == 1) {
                state = "On;"
            }
            main_el.textContent = state + unit;
            main_el.className = "ui-li-aside";
        }
        else {
            main_el = document.createElement("h1");
            main_el.textContent = value + unit;
            main_el.className = "ui-li-aside";
        }

        main_el.id = ns + "_value";

        //create label
        label = document.createElement("label");
        label.id = ns + "_label";
        label.setAttribute("for", main_el.id);
        label.textContent = name;

        //create structure
        div.appendChild(label);
        // if (device == "input") { div.appendChild(cfg_el); div.appendChild(cnt_el);}
        div.appendChild(main_el);
        li.appendChild(div);

        //and append it to the html
        if (device == 'ai') {
            var divider = document.getElementById("unipi_temp_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (device == 'ao') {
            $('#outputs_list').append(li);
            $('#' + main_el.id).slider();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("slidestop", function (event, ui) {
                makePostRequest('ao/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (device == 'relay') {
            var divider = document.getElementById("unipi_ao_divider");
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('relay/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (device == 'input') {
            var divider = document.getElementById("unipi_ai_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (device == 'temp' || device == '1wdevice') {
            $('#inputs_list').append(li);
            $('#inputs_list').listview('refresh');
        }
    }
    else {
        //get elements
        var main_el = document.getElementById(ns + "_value");
        var label = document.getElementById(ns + "_label");
        //and update values
        label.textContent = name;
        //outputs
        if (device == 'relay') {
            //TODO: remove re-binding when/if more events for flispwitch are available to prevent looping
            //unbind to prevent looping
            $('#' + main_el.id).unbind("change");
            $("#" + ns + "_value").val(value).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('relay/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (device == 'ao') {
            $("#" + ns + "_value").val(value).slider("refresh");
        }
        //inputs
        else if (device == 'input') {
            //if (msg.counter_mode != "disabled") {
                //var counter_el = document.getElementById(ns + "_counter");
                //counter_el.innerHTML = counter;
            //}
            main_el.innerHTML = (value == 1) ? "On" : "Off";
        }
        else {
            main_el.innerHTML = value + unit;
        }
    }
}

function update_values() {
    $.ajax({
        url: 'rest/all',
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
            if (msg.constructor === Array) {
                data = sortResults(msg);
                $.each(data, function (name, msg) {
                    SyncDevice(msg);
                });
            } else {
                SyncDevice(msg);
            }
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

function makePostRequest(action, params) {
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
