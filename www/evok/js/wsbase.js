$.fn.exists = function () {
    return this.length !== 0;
}

$.postJSON = function(url, data, success, args) {
	  args = $.extend({
	    url: url,
	    type: 'POST',
	    data: JSON.stringify(data),
	    contentType: 'application/json; charset=utf-8',
	    dataType: 'json',
	    async: true,
	    success: success
	  }, args);
	  return $.ajax(args);
};

var legacy_api = false;
var api_port = location.port || (location.protocol === 'https:' ? '443' : '80');

var ws = null;
var use_polling = false;
var timer = null;


function compare(a,b) {
	  if (a.circuit < b.circuit)
	    return -1;
	  if (a.circuit > b.circuit)
	    return 1;
	  return 0;
}


function sortResults(data) {
    return data.sort(compare);
}

function SyncDevice(msg) {
    //todo: add name as parameter
    var name = "";
    var circuit = msg.circuit;
    var circuit_display_name = circuit.replace(/\_/g, ' ');
    var device = msg.dev;
    var typ = msg.typ;
    var value = msg.value;
    var humidity = "N/A";
    var unit = "";
    var ns = "unipi_" + device + "_" + circuit;
	var neuron_sn = 0;
	var neuron_name = "";
	var uart_speed_modes = [""]
	var uart_speed_mode = ""
	var uart_parity_modes = [""]
	var uart_parity_mode = ""
	var uart_stopb_modes = [""]
	var uart_stopb_mode = ""
	var watchdog_timeout = 5000
	var watchdog_nv_save = 0
	var watchdog_reset = 0
	var watchdog_was_wd_reset = 0
    if (device == 'ai') {
        name = "Analog Input " + circuit_display_name;
        value = msg.value.toFixed(3);
        unit = "V";
    }
    else if (device == 'ao') {
        name = "Analog Output " + circuit_display_name;
        unit = "V";
        value = msg.value.toFixed(1);
    }
    else if (device == 'relay') {
        name = "Relay " + circuit_display_name;
    	if (("relay_type" in msg) && msg.relay_type == "digital") {
    		name = "Digital Output " + circuit_display_name;
    	}
    }
    else if (device == 'led') {
        name = "ULED " + circuit_display_name;
    }
    else if (device == 'input') {
        name = "Input " + circuit_display_name;
        counter = msg.counter;
    }
    else if (device == 'uart') {
    	name = "UART Port " + circuit_display_name;
    	uart_speed_modes = msg.speed_modes
    	uart_speed_mode = msg.speed_mode
    	uart_parity_modes = msg.parity_modes
    	uart_parity_mode = msg.parity_mode
    	uart_stopb_modes = msg.stopb_modes
    	uart_stopb_mode = msg.stopb_mode
    }
    else if (device == 'wd') {
    	name = "Board Watchdog " + circuit_display_name;
    	watchdog_timeout = msg.timeout[0]
    	watchdog_nv_save = msg.nv_save
    	watchdog_reset = msg.reset
    	watchdog_was_wd_reset = msg.was_wd_reset
    }
    else if (device == 'temp' || device == '1wdevice') {
        name = "Sensor " + typ + " - " + circuit_display_name;
        if (msg.value == null) {
            value = "N/A";
        }
        else {
            value = msg.value.toFixed(1);
            unit = "°C";
        }
    }
    else if (device == '1wdevice' && typ == 'DS2438') {
        name = "" + typ + " - " + circuit_display_name;
        if (msg.value == null) {
            value = "N/A";
            humidity = "N/A";
        }
        else {
            value = msg.temp.toFixed(1);
            humidity = msg.humidity.toFixed(1);
            unit = "°C";
        }   	
    } else if (device == 'neuron') {
    	neuron_sn = msg.sn
    	neuron_name = msg.model
    	name = "Neuron " + neuron_name;
    }
    //todo: unite names of device types here and in evok
    if (!$('#' + ns + '_li').length > 0) {
        li = document.createElement("li");
        li.id = ns + "_li";

        div = document.createElement("div");
        div.className = "ui-field-contain";

        if (device == 'relay' || device == 'led') {
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
        else if (device == "temp") {
            main_el = document.createElement("h1");
        	main_el.textContent = value + unit;
            main_el.className = "ui-li-aside";
        }
        else if (device == "1wdevice") {
            main_el = document.createElement("h1");
            main_el.textContent = "" + humidity + "%Hum " + value + unit;
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
        else if (device == "neuron") {
            main_el = document.createElement("h1");
            if (neuron_sn != null) {
            	main_el.textContent = "S/N: " + neuron_sn;
            } else {
            	main_el.textContent = "";
            }
            main_el.className = "ui-li-aside";
        }
        else if (device == "uart") {
            main_el = document.createElement("h1");
        	main_el.textContent = "Speed: " + uart_speed_mode + " Parity: " + uart_parity_mode;
            main_el.className = "ui-li-aside";
        }
        else if (device == 'wd') {
            main_el = document.createElement("h1");
            var enabled_text = "";
            if (value == 1) {
            	enabled_text = "[Enabled]"
            } else {
            	enabled_text = "[Disabled]"
            }
            if (watchdog_was_wd_reset == 0) {
            	main_el.textContent = enabled_text + " [Not Triggered] " + "Timeout: " + watchdog_timeout;
            } else {
            	main_el.textContent = enabled_text + " [Reset Triggered] " + "Timeout: " + watchdog_timeout;
            }
        	
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
        else if (device == 'led') {
            var divider = document.getElementById("unipi_ao_divider");
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('led/' + circuit, 'value=' + $(this).val());
            });        	
        }
        else if (device == 'relay') {
            var divider = document.getElementById("unipi_led_divider");
        	if (("relay_type" in msg) && msg.relay_type == "digital") {
        		divider = document.getElementById("unipi_relay_divider");
        	} 
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                //makePostRequest('relay/' + circuit, 'value=' + $(this).val());
            	$.postJSON('relay/' + circuit, {value: $(this).val})
            });
        }
        else if (device == 'input') {
            var divider = document.getElementById("unipi_ai_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (device == 'input') {
            var divider = document.getElementById("unipi_ai_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        }
        else if (device == 'temp') {
            $('#inputs_list').append(li);
            $('#inputs_list').listview('refresh');
        }
        else if (device == '1wdevice' && typ == 'DS2438') {
            $('#inputs_list').append(li);
            $('#inputs_list').listview('refresh');        	
        }
        else if (device == 'neuron') {
            var divider = document.getElementById("unipi_uart_divider");
            var list = document.getElementById("system_list");
            list.insertBefore(li, divider);
            $('#system_list').listview('refresh');             
        }
        else if (device == "uart") {
            var divider = document.getElementById("unipi_watchdog_divider");
            var list = document.getElementById("system_list");
            list.insertBefore(li, divider);
            $('#system_list').listview('refresh'); 
        }
        else if (device == 'wd') {
        	$('#system_list').append(li);
        	$('#system_list').listview('refresh'); 
        }
    } else {
        //get elements
        var main_el = document.getElementById(ns + "_value");
        var label = document.getElementById(ns + "_label");
        //and update values
        label.textContent = name;
        //outputs
        if (device == 'relay') {
            //unbind to prevent looping
        	$('#' + main_el.id).unbind("change");
            $("#" + ns + "_value").val(value).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('relay/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (device == 'led') {
            //unbind to prevent looping
            $('#' + main_el.id).unbind("change");
            $("#" + ns + "_value").val(value).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('led/' + circuit, 'value=' + $(this).val());
            });
        }
        else if (device == 'ao') {
            $("#" + ns + "_value").val(value).slider("refresh");
        }
        //inputs
        else if (device == 'input') {
            if (msg.counter_mode != "Disabled") {
               var counter_el = document.getElementById(ns + "_counter");
               //counter_el.innerHTML = counter;
            }
            main_el.innerHTML = (value == 1) ? "On" : "Off";
        }
        else if (device == '1wdevice' && typ == 'DS2438') {
        	main_el.innerHTML = "" + humidity + "%Hum " + value + unit;       	
        }
        else if (device == 'neuron') {
            if (neuron_sn != null) {
            	main_el.innerHTML = "S/N: " + neuron_sn;
            } else {
            	main_el.innerHTML = "";
            }
        }
        else if (device == 'uart') {
        	main_el.innerHTML  = "Speed: " + uart_speed_mode + " Parity: " + uart_parity_mode;
        }
        else if (device == 'wd') {
            var enabled_text = "";
            if (value == 1) {
            	enabled_text = "[Enabled]"
            } else {
            	enabled_text = "[Disabled]"
            }
            if (watchdog_was_wd_reset == 0) {
            	main_el.innerHTML = enabled_text + " [Not Triggered] " + "Timeout: " + watchdog_timeout;
            } else {
            	main_el.innerHTML = enabled_text + " [Reset Triggered] " + "Timeout: " + watchdog_timeout;
            }
        }
        else {
            main_el.innerHTML = value + unit;
        }
    }
}

function update_values() {
	if (legacy_api) {
	    $.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/all',
	        dataType: 'json',
	        success: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'hidden');
	            data = sortResults(data);
	            $.each(data, function (name, msg) {
	                SyncDevice(msg);
	            });
	        },
	        error: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'visible');
	        }
	    });
    } else {
	    $.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/all',
	        dataType: 'json',
	        success: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'hidden');
	            data = sortResults(data.data);
	            $.each(data, function (name, msg) {
	                SyncDevice(msg);
	            });
	        },
	        error: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'visible');
	        }
	    });    	
    }
}





function WebSocketRegister() {
    if ("WebSocket" in window) {
        if (ws) {
            return
        }
        var loc = window.location;
        uri = ((loc.protocol === "https:") ? "wss://" : "ws://") + loc.hostname + ':' + api_port;

        ws = new WebSocket(uri + "/ws");
        //var wnd = null;

        if (!ws) {
            setTimeout(WebSocketRegister, 1000);
            return;
        }

        window.onbeforeunload = function () {
            ws.onclose = function () {
            }; 
            ws.close()
        };

        ws.onopen = function () {
            update_values();
        };

        ws.onmessage = function (evt) {
            var received_msg = evt.data;
            var msg = JSON.parse(evt.data);
			$("#unipi_loading_spinner").css('visibility', 'hidden');
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
		
		ws.onerror = function () {
			$("#unipi_loading_spinner").css('visibility', 'visible');
		};
    }
    else {
        alert("WebSocket NOT supported by your Browser!");
        use_polling = true;
    }
}

function makePostRequest(action, params) {
	 if (legacy_api) {
		$.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/' + action,
	        type: 'POST',
	        data: params,
	        success: function (data) {
	        },
	        error: function (data) {
	        }
	    });
	} else {
		var to_send = {};

		$.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/' + action,
	    	dataType: "application/json",
	        type: 'POST',
	        data: JSON.stringify(params),
	        success: function (data) {
	        },
	        error: function (data) {
	        }
	    });
	}
}
