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

var legacy_api = true;
var api_port = location.port || (location.protocol === 'https:' ? '443' : '80');

var ws = null;
var use_polling = false;
var timer = null;

var device_counts = {};


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


function populateConfigForm(form, device, circuit) {
	switch(device) {
	case "ai": {
		mode_select_field = $("<select>", {"name": "unipi_config_form_mode_select_field", "data-iconpos":"left"});
		mode_label = $("<label>", {"for": "unipi_config_form_range_select_field"});
		mode_label.text("Mode:");
		range_label = $("<label>", {"for": "unipi_config_form_range_select_field"});
		range_label.text("Range:");
		alias_label = $("<label>", {"for": "unipi_config_form_alias_field"});
		
		break;
	}
	case "ao": {
		return "Analog Output Configuration";
		break;
	}
	case "relay": {
		return "Relay Output Configuration";
	}
	case "led": {
		return "User LED Configuration";
	}
	case "input": {
		return "Digital Input Configuration";
	}
	case "uart": {
		return "UART Port Configuration";
	}
	case "wd": {
		return "Board Watchdog Configuration";
	}
	case "temp": {
		return "Temperature Sensor Configuration";
	}
	case "1wdevice": {
		return "1Wire Device Configuration";
	}
	case "neuron": {
		return "PLC Device Configuration";
	}
	case "wifi": {
		return "WiFi Adapter Configuration";
	}
	case "register": {
		return "Modbus Register Configuration";
	}
	default: {
		return "Unknown Device Type Configuration";
		break;
	}
	}
}

function getConfigurationFormTitle(device) {
	switch(device) {
	case "ai": {
		return "Analog Input Configuration";
		break;
	}
	case "ao": {
		return "Analog Output Configuration";
		break;
	}
	case "relay": {
		return "Relay Output Configuration";
	}
	case "led": {
		return "User LED Configuration";
	}
	case "input": {
		return "Digital Input Configuration";
	}
	case "uart": {
		return "UART Port Configuration";
	}
	case "wd": {
		return "Board Watchdog Configuration";
	}
	case "temp": {
		return "Temperature Sensor Configuration";
	}
	case "1wdevice": {
		return "1Wire Device Configuration";
	}
	case "neuron": {
		return "PLC Device Configuration";
	}
	case "wifi": {
		return "WiFi Adapter Configuration";
	}
	case "register": {
		return "Modbus Register Configuration";
	}
	default: {
		return "Unknown Device Type Configuration";
		break;
	}
	}
}


function getNextUiBlockPosition(device) {
	switch ((device_counts[device] - 1) % 5) {
	case 0: {
		return "ui-block-a";
		break;
	}
	case 1: {
		return "ui-block-b";
		break;
	}
	case 2: {
		return "ui-block-c";
		break;
	}
	case 3: {
		return "ui-block-d";
		break;
	}
	case 4: {
		return "ui-block-e";
		break;
	}
	}
}

function getDeviceCategoryName(device) {
	switch(device) {
	case "ai": {
		return "Analog Inputs";
		break;
	}
	case "ao": {
		return "Analog Outputs";
		break;
	}
	case "relay": {
		return "Relay Outputs";
	}
	case "led": {
		return "User LEDs";
	}
	case "input": {
		return "Digital Inputs";
	}
	case "uart": {
		return "UART Ports";
	}
	case "wd": {
		return "Board Watchdogs";
	}
	case "temp": {
		return "Temperature Sensors";
	}
	case "1wdevice": {
		return "1Wire Devices";
	}
	case "neuron": {
		return "PLC Devices";
	}
	case "wifi": {
		return "WiFi Adapters";
	}
	case "register": {
		return "Modbus Registers";
	}
	default: {
		return "Unknown Device Type";
		break;
	}
	}
}

function SyncDevice(msg) {
    var name = "";
    var circuit = msg.circuit;
    var circuit_display_name = circuit.replace(/\_/g, ' ');
    if (circuit_display_name.substring(circuit_display_name.length - 3,circuit_display_name.length - 2) == ' ') {
    	circuit_display_name = circuit_display_name.substring(0,circuit_display_name.length - 3) + '.' + circuit_display_name.substring(circuit_display_name.length - 2, circuit_display_name.length);
    }
    var device = msg.dev;
    var typ = msg.typ;
    var value = msg.value;
    var humidity = "N/A";
    var unit = "";
    var ns = "unipi_" + device + "_" + circuit;
	var neuron_sn = 0;
	var neuron_name = "";
	var uart_speed_modes = [""];
	var uart_speed_mode = "";
	var uart_parity_modes = [""];
	var uart_parity_mode = "";
	var uart_stopb_modes = [""];
	var uart_stopb_mode = "";
	var watchdog_timeout = 5000;
	var watchdog_nv_save = 0;
	var watchdog_reset = 0;
	var watchdog_was_wd_reset = 0;
	var wifi_ap_state = 0;
	var wifi_eth0_masq = 0;
	
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
    	uart_speed_modes = msg.speed_modes;
    	uart_speed_mode = msg.speed_mode;
    	uart_parity_modes = msg.parity_modes;
    	uart_parity_mode = msg.parity_mode;
    	uart_stopb_modes = msg.stopb_modes;
    	uart_stopb_mode = msg.stopb_mode;
    }
    else if (device == 'wd') {
    	name = "Board Watchdog " + circuit_display_name;
    	watchdog_timeout = msg.timeout[0];
    	watchdog_nv_save = msg.nv_save;
    	watchdog_reset = msg.reset;
    	watchdog_was_wd_reset = msg.was_wd_reset;
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
    	neuron_sn = msg.sn;
    	neuron_name = msg.model;
    	name = "Neuron " + neuron_name;
    } else if (device == 'wifi') {
		name = "WiFi Adapter " + circuit_display_name;
    	wifi_ap_state = msg.ap_state;
    	wifi_eth0_masq = msg.eth0_masq;
    }

    if (!$('#' + ns + '_li').length > 0 && device != 'register') {
        li = document.createElement("li");
        li.id = ns + "_li";

    	if (device in device_counts) {
    		device_counts[device] += 1;
    	} else {
    		device_counts[device] = 1;
            config_div = document.createElement("div");
            config_div.id = "unipi_" + device + "_config_div";
            config_div_label = document.createElement("h4");
            config_div_label.id = "unipi_" + device + "_config_div_label";
            config_div_label.textContent = getDeviceCategoryName(device);
            config_div_grid = document.createElement("div");
            config_div_grid.id = "unipi_" + device + "_config_div_grid";
            config_div_grid.className = "ui-grid-d ui-responsive"; 
            config_div.appendChild(config_div_label);
            config_div.appendChild(config_div_grid);
            document.getElementById("configs").appendChild(config_div);
    	}
        
    	config_el_div = document.createElement("div");
    	config_el_div.id = "unipi_" + device + "_" + msg.circuit + "_config_div";
    	config_el_div.className = getNextUiBlockPosition(device);
    	config_el = document.createElement("a");
    	config_el.id = "unipi_config_div_grid_anchor_" + msg.circuit;
    	config_el.className = "ui-btn ui-shadow ui-corner-all";
    	config_el.textContent = circuit_display_name;
    	config_el.href = "#" + device;
    	config_el_div.appendChild(config_el);
    	$(config_el).on("click", (event) => configButtonHandler(event));
        document.getElementById("unipi_" + device + "_config_div_grid").appendChild(config_el_div);
        
        
        div = document.createElement("div");
        div.className = "ui-field-contain";
        
        right_div = document.createElement("div");
        right_div.style = "float: right;"

        if (device == 'relay' || device == 'led') {
            main_el = document.createElement("select");
            main_el.className = "ui-btn-right";
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
            
        }
        else if (device == "neuron") {
            main_el = document.createElement("h1");
            if (neuron_sn != null) {
            	main_el.textContent = "S/N: " + neuron_sn;
            } else {
            	main_el.textContent = "";
            }
        }
        else if (device == "uart") {
            main_el = document.createElement("h1");
        	main_el.textContent = "Speed: " + uart_speed_mode + " Parity: " + uart_parity_mode;
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
        }
        else if (device == 'wifi') {
            main_el = document.createElement("select");
            var option_on = document.createElement("option");
            option_on.value = "Enabled";
            option_on.textContent = "On";
            var option_off = document.createElement("option");
            option_off.value = "Disabled";
            option_off.textContent = "Off";
            main_el.add(option_off);
            main_el.add(option_on);
        }
        else {
            main_el = document.createElement("h1");
            main_el.textContent = value + unit;
        }

        main_el.id = ns + "_value";

        //create label
        label = document.createElement("label");
        label.id = ns + "_label";
        label.setAttribute("for", main_el.id);
        label.textContent = name;

        //create structure
        div.appendChild(label);
        if (device == "ao") { 
        	div.appendChild(main_el);
        } else {
        	div.appendChild(right_div); 
        	right_div.appendChild(main_el);
        }
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
        	var divider = document.getElementById("unipi_wifi_divider");
            var list = document.getElementById("system_list");
            list.insertBefore(li, divider);
        	$('#system_list').listview('refresh'); 
        }
        else if (device == 'wifi') {
        	$('#system_list').append(li);
            $('#' + main_el.id).flipswitch();
            $('#system_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('wifi/' + circuit, 'ap_state=' + $(this).val());
            });   
        }
    } else if (device != 'register') {
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
        else if (device == 'wifi') {
            //unbind to prevent looping
            $('#' + main_el.id).unbind("change");
            $("#" + ns + "_value").val(wifi_ap_state).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('wifi/' + circuit, 'ap_state=' + $(this).val());
            });
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

function configButtonHandler(event) {
	var device = event.currentTarget.href.substr(event.currentTarget.origin.length + 2, (event.currentTarget.href.length));
	var circuit = event.currentTarget.id.substr(28, (event.currentTarget.id.length));
	//alert("Device: " + device + " Circuit: " + circuit);
	event.preventDefault();
    var circuit_display_name = circuit.replace(/\_/g, ' ');
    if (circuit_display_name.substring(circuit_display_name.length - 3,circuit_display_name.length - 2) == ' ') {
    	circuit_display_name = circuit_display_name.substring(0,circuit_display_name.length - 3) + '.' + circuit_display_name.substring(circuit_display_name.length - 2, circuit_display_name.length);
    }
	var config_device_header = $("<h3>", {id: "config_form_device_header"});
	config_device_header.text(getConfigurationFormTitle(device));
	var config_circuit_header = $("<h5>", {id: "config_form_circuit_header"});
	config_circuit_header.text(circuit_display_name);
	$("#unipi_config_form_inner_div").empty();
	$("#unipi_config_form_inner_div").append(config_device_header);
	$("#unipi_config_form_inner_div").append(config_circuit_header);
	$("#unipi_config_form_div").popup("open");
}


$(document).ready(function(){
	$("#unipi_config_form_test_button").on("click", (event) => configButtonHandler(event));
});


function configFormSubmitHandler() {
	
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
