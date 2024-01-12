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
var wd_device_cache = [];

function compare(a,b) {
	  if (a.circuit < b.circuit) {
		    return -1;	  
	  }
	  if (a.circuit > b.circuit) {
		    return 1;
	  }
	  return 0;
}


function sortResults(data) {
    return data.sort(compare);
}


function populateConfigForm(form, device, circuit, data) {
	var alias = "";
	if (data.hasOwnProperty("alias")) {
		alias = data.alias;
	}
	switch(device) {
	case "ai": {
		if (data.hasOwnProperty("modes") && data.hasOwnProperty("mode")) {
			var mode_select_field = $("<select>", {"name": "unipi_config_form_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_mode_select_field"});
			var mode_label = $("<label>", {"for": "unipi_config_form_mode_select_field"});
			mode_label.text("Mode:");
			var selected_mode = data.mode;
			$.each(data.modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				mode_select_field.append(option_field);
			});
			form.append([mode_label, mode_select_field]);
		}
		if (data.hasOwnProperty("range_modes") && data.hasOwnProperty("range")) {
			var range_select_field = $("<select>", {"name": "unipi_config_form_range_select_field", "data-iconpos": "left", "id": "unipi_config_form_range_select_field"});
			var range_label = $("<label>", {"for": "unipi_config_form_range_select_field"});
			range_label.text("Range:");
			var selected_mode = data.range;
			$.each(data.range_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				range_select_field.append(option_field);
			});
			form.append([range_label, range_select_field]);
		}
		break;
	}
	case "ao": {
		if (data.hasOwnProperty("modes") && data.hasOwnProperty("mode")) {
			var mode_select_field = $("<select>", {"name": "unipi_config_form_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_mode_select_field"});
			var mode_label = $("<label>", {"for": "unipi_config_form_mode_select_field"});
			mode_label.text("Mode:");
			var selected_mode = data.mode;
			$.each(data.modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				mode_select_field.append(option_field);
			});
			form.append([mode_label, mode_select_field]);
		}
		break;
	}
	case "relay": {
		if (data.hasOwnProperty("modes") && data.hasOwnProperty("mode")) {
			var mode_select_field = $("<select>", {"name": "unipi_config_form_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_mode_select_field"});
			var mode_label = $("<label>", {"for": "unipi_config_form_mode_select_field"});
			mode_label.text("Mode:");
			var selected_mode = data.mode;
			$.each(data.modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				mode_select_field.append(option_field);
			});
			form.append([mode_label, mode_select_field]);
		}
		if (data.hasOwnProperty("pwm_freq") && data.hasOwnProperty("pwm_duty")) {
			var pwm_freq_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_pwm_freq_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_pwm_freq_field", "value": data.pwm_freq});
			pwm_freq_label = $("<label>", {"for": "unipi_config_form_pwm_freq_field"});
			pwm_freq_label.text("PWM Frequency (in Hz):");
			var pwm_duty_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_pwm_duty_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_pwm_duty_field", "value": data.pwm_duty});
			pwm_duty_label = $("<label>", {"for": "unipi_config_form_pwm_duty_field"});
			pwm_duty_label.text("PWM Duty Cycle (in %):");
			form.append([pwm_freq_label, pwm_freq_text_field, pwm_duty_label, pwm_duty_text_field, ]);
		}
		break;
	}
	case "led": {
		break;
	}
	case "input": {
		if (data.hasOwnProperty("debounce")) {
			var debounce_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_debounce_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_debounce_field", "value": data.debounce});
			var debounce_label = $("<label>", {"for": "unipi_config_form_debounce_field"});
			debounce_label.text("Debounce:");
			form.append([debounce_label, debounce_text_field]);
		}
		if (data.hasOwnProperty("modes") && data.hasOwnProperty("mode")) {
			var mode_select_field = $("<select>", {"name": "unipi_config_form_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_mode_select_field"});
			var mode_label = $("<label>", {"for": "unipi_config_form_mode_select_field"});
			mode_label.text("Mode:");
			var selected_mode = data.mode;
			$.each(data.modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				mode_select_field.append(option_field);
			});
			form.append([mode_label, mode_select_field]);
		}
		if (data.hasOwnProperty("counter_mode") && data.hasOwnProperty("counter_modes")) {
			var counter_mode_select_field = $("<select>", {"name": "unipi_config_form_counter_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_counter_mode_select_field"});
			var counter_mode_label = $("<label>", {"for": "unipi_config_form_counter_mode_select_field"});
			counter_mode_label.text("Counter Mode:");
			var selected_mode = data.counter_mode;
			$.each(data.counter_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				counter_mode_select_field.append(option_field);
			});
			form.append([counter_mode_label, counter_mode_select_field]);
		}
		if (data.hasOwnProperty("counter")) {
			var counter_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_counter_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_counter_field", "value": data.counter});
			var counter_label = $("<label>", {"for": "unipi_config_form_counter_field"});
			counter_label.text("Counter value:");
			form.append([counter_label, counter_text_field]);
		}
		if (data.hasOwnProperty("ds_mode") && data.hasOwnProperty("ds_modes")) {
			var ds_mode_select_field = $("<select>", {"name": "unipi_config_form_ds_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_ds_mode_select_field"});
			var ds_mode_label = $("<label>", {"for": "unipi_config_form_ds_mode_select_field"});
			ds_mode_label.text("DirectSwitch Mode:");
			var selected_mode = data.ds_mode;
			$.each(data.ds_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				ds_mode_select_field.append(option_field);
			});
			form.append([ds_mode_label, ds_mode_select_field]);
		}
		break;
	}
	case "uart": {
		if (data.hasOwnProperty("parity_modes") && data.hasOwnProperty("parity_mode")) {
			var parity_mode_select_field = $("<select>", {"name": "unipi_config_form_parity_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_parity_mode_select_field"});
			var parity_mode_label = $("<label>", {"for": "unipi_config_form_parity_mode_select_field"});
			parity_mode_label.text("Parity:");
			var selected_mode = data.parity_mode;
			$.each(data.parity_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				parity_mode_select_field.append(option_field);
			});
			form.append([parity_mode_label, parity_mode_select_field]);
		}
		if (data.hasOwnProperty("speed_modes") && data.hasOwnProperty("speed_mode")) {
			var speed_mode_select_field = $("<select>", {"name": "unipi_config_form_speed_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_speed_mode_select_field"});
			var speed_mode_label = $("<label>", {"for": "unipi_config_form_speed_mode_select_field"});
			speed_mode_label.text("Speed:");
			var selected_mode = data.speed_mode;
			$.each(data.speed_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				speed_mode_select_field.append(option_field);
			});
			form.append([speed_mode_label, speed_mode_select_field]);
		}
		if (data.hasOwnProperty("stopb_modes") && data.hasOwnProperty("stopb_mode")) {
			var stopb_mode_select_field = $("<select>", {"name": "unipi_config_form_stopb_mode_select_field", "data-iconpos": "left", "id": "unipi_config_form_stopb_mode_select_field"});
			var stopb_mode_label = $("<label>", {"for": "unipi_config_form_stopb_mode_select_field"});
			stopb_mode_label.text("Stopbits:");
			var selected_mode = data.stopb_mode;
			$.each(data.stopb_modes, function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				stopb_mode_select_field.append(option_field);
			});
			form.append([stopb_mode_label, stopb_mode_select_field]);
		}
		break;
	}
	case "wd": {
		if (data.hasOwnProperty("value")) {
			var enabled_select_field = $("<select>", {"name": "unipi_config_form_enabled_select_field", "data-iconpos": "left", "id": "unipi_config_form_enabled_select_field"});
			var enabled_label = $("<label>", {"for": "unipi_config_form_enabled_select_field"});
			enabled_label.text("Command Watchdog (reset device if no command in timeout ms):");
			var selected_mode = data.nv_save;
			$.each([0, 1], function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				if (value == 0) {
					option_field.text("Disabled");
				} else {
					option_field.text("Enabled");
				}
				enabled_select_field.append(option_field);
			});
			form.append([enabled_label, enabled_select_field]);
		}
		if (data.hasOwnProperty("timeout")) {
			var timeout_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_timeout_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_timeout_field", "value": data.timeout});
			var timeout_label = $("<label>", {"for": "unipi_config_form_timeout_field"});
			timeout_label.text("Command Watchdog trigger timeout (in ms):");
			form.append([timeout_label, timeout_text_field]);
		}
		if (data.hasOwnProperty("nv_save")) {
			var nv_save_select_field = $("<select>", {"name": "unipi_config_form_nv_save_select_field", "data-iconpos": "left", "id": "unipi_config_form_nv_save_select_field"});
			var nv_save_label = $("<label>", {"for": "unipi_config_form_nv_save_select_field"});
			nv_save_label.text("Save Current Board Configuration As Default On Manual Reset:");
			var selected_mode = data.nv_save;
			$.each([0, 1], function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				if (value == 0) {
					option_field.text("Disabled");
				} else {
					option_field.text("Enabled");
				}
				nv_save_select_field.append(option_field);
			});
			form.append([nv_save_label, nv_save_select_field]);
		}
		if (data.hasOwnProperty("was_wd_reset")) {
			var wd_reset_select_field = $("<select>", {"name": "unipi_config_form_wd_reset_select_field", "data-iconpos": "left", "id": "unipi_config_form_wd_reset_select_field"});
			var wd_reset_label = $("<label>", {"for": "unipi_config_form_wd_reset_select_field"});
			wd_reset_label.text("Perform Manual Reset:");
			var selected_mode = 0;
			$.each([0, 1], function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				if (value == 0) {
					option_field.text("No");
				} else {
					option_field.text("Yes");
				}
				wd_reset_select_field.append(option_field);
			});
			form.append([wd_reset_label, wd_reset_select_field]);
		}
		break;
	}
	case "temp": {
		break;
	}
	case "1wdevice": {
		break;
	}
	case "device_info": {
		break;
	}
	case "wifi": {
		if (data.hasOwnProperty("ap_state")) {
			var ap_state_select_field = $("<select>", {"name": "unipi_config_form_ap_state_select_field", "data-iconpos": "left", "id": "unipi_config_form_ap_state_select_field"});
			var ap_state_label = $("<label>", {"for": "unipi_config_form_ap_state_select_field"});
			ap_state_label.text("Access Point:");
			var selected_mode = data.ap_state;
			$.each(["Enabled", "Disabled"], function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				ap_state_select_field.append(option_field);
			});
			form.append([ap_state_label, ap_state_select_field]);
		}
		if (data.hasOwnProperty("eth0_masq")) {
			var eth0_masq_select_field = $("<select>", {"name": "unipi_config_form_eth0_masq_select_field", "data-iconpos": "left", "id": "unipi_config_form_eth0_masq_select_field"});
			var eth0_masq_label = $("<label>", {"for": "unipi_config_form_eth0_masq_select_field"});
			eth0_masq_label.text("Ethernet-WiFi Masquerade (Bridge Mode):");
			var selected_mode = data.eth0_masq;
			$.each(["Enabled", "Disabled"], function(index, value) {
				var option_field;
				if (selected_mode == value) {
					option_field = $("<option>", {"value": value, "selected":"selected"});
				}
				else {
					option_field = $("<option>", {"value": value});
				}
				option_field.text(value);
				eth0_masq_select_field.append(option_field);
			});
			form.append([eth0_masq_label, eth0_masq_select_field]);
		}
		break;
	}
	case "register": {
		break;
	}
	case "light_channel": {
		break;
	}
	default: {
		break;
	}
	}
	var circuit_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_circuit_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_circuit_field", "value": circuit});
	var circuit_field_label = $("<label>", {"for": "unipi_config_form_circuit_field"});
	var device_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_device_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_device_field", "value": device});
	var device_field_label = $("<label>", {"for": "unipi_config_form_device_field"});
	form.append([circuit_field_label, circuit_text_field, device_field_label, device_text_field]);

	if (device != "device_info") {
		if (device != "wifi" && device != "wd") {
			var decoded_alias = alias;
			decoded_alias = decoded_alias.replace(/_/g," ");
			alias_text_field = $("<input>", {"type":"text", "name": "unipi_config_form_alias_field", "data-wrapper-class": "ui-btn", "id": "unipi_config_form_alias_field", "value": decoded_alias});
			alias_label = $("<label>", {"for": "unipi_config_form_alias_field"});
			alias_label.text("Alias:");
			form.append([alias_label, alias_text_field]);
		}
		submit_button = $("<input>", {"type": "submit", "value": "Submit", "id":"unipi_config_form_submit_button"});
		form.append([submit_button]);
	} else {
		print_button = $("<input>", {"type": "submit", "value": "Print Log", "id":"unipi_config_form_print_button"});
		form.append([print_button]);
	}
	$("#unipi_config_form").on("submit", function(event) {configFormSubmitHandler(event);});
	form.trigger('create');
	circuit_text_field.parent().hide();
	circuit_field_label.hide();
	device_text_field.parent().hide();
	device_field_label.hide();
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
	case "device_info": {
		return "PLC Device Configuration";
	}
	case "wifi": {
		return "WiFi Adapter Configuration";
	}
	case "register": {
		return "Modbus Register Configuration";
	}
	case "light_channel": {
		return "Lighting Channel Configuration";
	}
	default: {
		return "Unknown Device Type Configuration" + device;
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
		return "Serial Ports";
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
	case "device_info": {
		return "EVOK Devices";
	}
	case "modbus_slave": {
		return "Modbus slave";
	}
	case "wifi": {
		return "WiFi Adapters";
	}
	case "register": {
		return "Modbus Registers";
	}
	case "unit_register": {
		return "Modbus Registers";
	}
	case "do": {
		return "Digital Outputs";
	}
	case "light_channel": {
		return "Lighting Bus Channels";
	}
	default: {
		return "Unknown Device Type";
		break;
	}
	}
}

function populateConfigTab(device, circuit, circuit_display_name, msg) {

    var translated_device = device;

    if (translated_device == "relay") {
    	if (("relay_type" in msg) && msg.relay_type == "digital") {
    		translated_device = "do";
    	}
    }
	if (translated_device in device_counts) {
		device_counts[translated_device] += 1;
	} else {
		device_counts[translated_device] = 1;
        config_div = document.createElement("div");
        config_div.id = "unipi_" + translated_device + "_config_div";
        config_div_label = document.createElement("h4");
        config_div_label.id = "unipi_" + translated_device + "_config_div_label";
        config_div_label.textContent = getDeviceCategoryName(translated_device);
        config_div_grid = document.createElement("div");
        config_div_grid.id = "unipi_" + translated_device + "_config_div_grid";
        config_div_grid.className = "ui-grid-d ui-responsive"; 
        config_div.appendChild(config_div_label);
        config_div.appendChild(config_div_grid);
        document.getElementById("configs").appendChild(config_div);
	}
    
	config_el_div = document.createElement("div");
	config_el_div.id = "unipi_" + device + "_" + msg.circuit + "_config_div";
	config_el_div.className = getNextUiBlockPosition(translated_device);
	config_el = document.createElement("a");
	config_el.id = "unipi_config_div_grid_anchor_" + device + "_" + msg.circuit;
	config_el.className = "ui-btn ui-shadow ui-corner-all";
	config_el.textContent = circuit_display_name;
	config_el.href = "#" + device;
	config_el_div.appendChild(config_el);
	$(config_el).on("click", function(event) {configButtonHandler(event);});
    document.getElementById("unipi_" + translated_device + "_config_div_grid").appendChild(config_el_div);
}

function getDeviceDisplayName() {
	
}

function extractDeviceProperties(device, circuit, circuit_display_name, msg) {
	var device_properties = {};
    device_properties["device_name"] = "";
    device_properties["typ"] = msg.typ;
    device_properties["value"] = msg.value;
    device_properties["humidity"] = "N/A";
    device_properties["unit"] = "";
    device_properties["device_info_sn"] = 0;
    device_properties["device_info_name"] = "";
    device_properties["uart_speed_modes"] = [""];
    device_properties["uart_speed_mode"]= "";
    device_properties["uart_parity_modes"] = [""];
    device_properties["uart_parity_mode"] = "";
    device_properties["uart_stopb_modes"] = [""];
    device_properties["uart_stopb_mode"] = "";
    device_properties["watchdog_timeout"] = 5000;
    device_properties["watchdog_nv_save"] = 0;
    device_properties["watchdog_reset"] = 0;
    device_properties["watchdog_was_wd_reset"] = 0;
    device_properties["wifi_ap_state"] = 0;
    device_properties["wifi_eth0_masq"] = 0;
	switch(device) {
	case "ai": {
		device_properties["device_name"] = "Analog Input " + circuit_display_name;
		device_properties["value"] = msg.value.toFixed(3);
		if ("unit" in msg) {
			device_properties["unit"] = msg.unit;
			if (msg.unit == ""){
				device_properties["value"] = msg.value;
			}
		} else {
			device_properties["unit"] = "V";
		}
		break;
	}
	case "ao": {
		device_properties["device_name"] = "Analog Output " + circuit_display_name;
        if ("unit" in msg) {
        	device_properties["unit"] = msg.unit;
        } else {
        	device_properties["unit"] = "V";
        }
        device_properties["value"] = msg.value.toFixed(1);
		break;
	}
	case "relay": {
		device_properties["device_name"] = "Relay " + circuit_display_name;
    	if (("relay_type" in msg) && msg.relay_type == "digital") {
    		device_properties["device_name"] = "Digital Output " + circuit_display_name;
    	}
		break;
	}
	case "led": {
		device_properties["device_name"] = "ULED " + circuit_display_name;
		break;
	}
	case "input": {
		device_properties["device_name"] = "Input " + circuit_display_name;
        device_properties["counter"] = msg.counter;
        if ("bitvalue" in msg) {
        	device_properties["bitvalue"] = msg.bitvalue;
        }
		break;
	}
	case "uart": {
		device_properties["device_name"] = "Serial Port " + circuit_display_name;
    	device_properties["uart_speed_modes"] = msg.speed_modes;
    	device_properties["uart_speed_mode"] = msg.speed_mode;
    	device_properties["uart_parity_modes"] = msg.parity_modes;
    	device_properties["uart_parity_mode"] = msg.parity_mode;
    	device_properties["uart_stopb_modes"] = msg.stopb_modes;
    	device_properties["uart_stopb_mode"] = msg.stopb_mode;
		break;
	}
	case "wd": {
		device_properties["device_name"] = "Board Watchdog " + circuit_display_name;
    	device_properties["watchdog_timeout"] = msg.timeout[0];
    	device_properties["watchdog_nv_save"] = msg.nv_save;
    	device_properties["watchdog_reset"] = msg.reset;
    	device_properties["watchdog_was_wd_reset"] = msg.was_wd_reset;
		break;
	}
	case "temp": {}
	case "1wdevice": {
		if (device_properties["typ"] == "DS2438") {
			device_properties["device_name"] = "Sensor " + "1W-TH" + " - " + circuit_display_name;
	        if (msg.temp == null) {
	        	device_properties["value"] = "N/A";
	        	device_properties["humidity"] = "N/A";
	        }
	        else {
	        	device_properties["value"] = parseFloat(msg.temp).toFixed(1);
	        	device_properties["humidity"] = msg.humidity.toFixed(1);
	        	device_properties["unit"] = "&deg;C";
	        }   	
		} else {
			device_properties["device_name"] = "Sensor " + device_properties["typ"] + " - " + circuit_display_name;
	        if (msg.value == null) {
	        	device_properties["value"] = "N/A";
	        }
	        else {
	        	device_properties["value"] = msg.value.toFixed(1);
	        	device_properties["unit"] = "&deg;C";
	        }
		}
		break;
	}
	case "device_info": {
		device_properties["device_info_sn"] = msg.sn;
		device_properties["device_info_name"] = msg.model;
		device_properties["device_info_family"] = msg.family;
		device_properties["device_name"] = device_properties["device_info_family"] + " " + device_properties["device_info_name"];
		break;
	}
	case "modbus_slave": {
		device_properties["device_name"] = "Modbus device: " + msg.circuit;
		device_properties["device_slave_id"] = msg.slave_id
		break;
	}
	case "wifi": {
		device_properties["device_name"] = "WiFi Adapter " + circuit_display_name;
		device_properties["wifi_ap_state"] = msg.ap_state;
		device_properties["wifi_eth0_masq"] = msg.eth0_masq;
		break;
	}
	case "light_channel": {
		device_properties["device_name"] = "light Channel " + circuit_display_name;
		device_properties["broadcast_commands"] = msg.broadcast_commands;
		break;
	}
    case "unit_register": {
            if (msg.value.toString().includes(".")){
                device_properties["value"] = msg.value.toFixed(2);
            }
            device_properties["device_name"] = "Value register " + circuit_display_name + " <br>" + msg.name;
            device_properties["unit"] = msg.unit;
            break;
    }
	}
    if ("alias" in msg) {
    	device_properties["device_name"] = circuit_display_name;
    }
    return device_properties;
}

function syncDevice(msg) {



    var circuit = msg.circuit;
    var device = msg.dev;
    var device_signature = "unipi_" + device + "_" + circuit;
    var circuit_display_name = circuit.replace(/\_/g, ' ');

    if(circuit_display_name.includes(" ")){
        var pos = circuit_display_name.lastIndexOf(" ");
        circuit_display_name = circuit_display_name.substring(0,pos) + '.' + circuit_display_name.substring(pos + 1, circuit_display_name.length);
    }

	// Change alias back into text
	if ("alias" in msg) {
		var decoded_alias = msg.alias;
		decoded_alias = decoded_alias.replace(/_/g," ");
		circuit_display_name = decoded_alias;
	}

    // Dictionary for parsed message values; initialised with default fallback values
    var device_properties = extractDeviceProperties(device, circuit, circuit_display_name, msg);

    if (!$('#' + device_signature + '_li').length > 0 && device != 'register' && device != 'owbus') {


        li = document.createElement("li");
        li.id = device_signature + "_li";

        if (device != "modbus_slave"){
            populateConfigTab(device, circuit, circuit_display_name, msg);
        }
        var div = document.createElement("div");
        div.className = "ui-field-contain";

        var right_div = document.createElement("div");
        right_div.style = "float: right;"

        switch (device) {
        case "relay": {}
        case "led": {
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
        	break;
        }
        case "ao": {
            main_el = document.createElement("input");
            main_el.className = "out";
            main_el.min = 0;
            main_el.step = 0.1;
            if (device_properties["unit"] == "V") {
            	main_el.max = 10;
            } else if (device_properties["unit"] == "mA") { 
                main_el.max = 20;
            }
            resistance_value_label = $("<h1>", {"className": "ul-li-aside"});
            resistance_value_label.text(device_properties["value"] + device_properties["unit"]);
        	break;
        }
        case "temp": {
            main_el = document.createElement("h1");
            main_el.innerHTML  = device_properties["value"] + " " + device_properties["unit"];
            //main_el.className = "ui-li-aside";
            break;
        }
        case "1wdevice": {
            main_el = document.createElement("h1");
            main_el.innerHTML = "" + device_properties["humidity"] + " %<br>" + device_properties["value"] + " " +device_properties["unit"];
            //main_el.className = "ui-li-aside";    
            break;
        }
        case "input": {
            cnt_el = document.createElement("h1");
            cnt_el.textContent = device_properties["counter"];
            cnt_el.className = "ui-li-aside";
            cnt_el.style = "right: 7em";
            cnt_el.id = device_signature + "_counter";

            cfg_el = document.createElement("a");
            cfg_el.className = "ui-icon-gear ui-btn-icon-notext ui-corner-all";
            cfg_el.href = "#popupBasic"; 
            cfg_el.setAttribute("data-rel","popup"); 
            cfg_el.setAttribute("data-position-to","window");
            cfg_el.setAttribute("data-transition","pop"); 
            cfg_el.id = device_signature + "_cfg";

            main_el = document.createElement("h1");
            var state = "Off";
            if ("bitvalue" in device_properties) {
            	if (device_properties["bitvalue"] == 1) {
            		state = "On";
            	}
            } else {
                if (device_properties["value"] == 1) {
                    state = "On";
                }            	
            }

            main_el.textContent = state + device_properties["unit"];
        	break;
        }
        case "device_info": {
            main_el = document.createElement("h1");
            if (device_properties["device_info_sn"] != null) {
            	main_el.textContent = "S/N: " + device_properties["device_info_sn"];
            } else {
            	main_el.textContent = "";
            }
        	break;
        }
        case "modbus_slave": {
            main_el = document.createElement("h1");
            main_el.textContent = "Address: " + device_properties["device_slave_id"];
            break;
        }
        case "uart": {
            main_el = document.createElement("h1");
        	main_el.textContent = "Speed: " + device_properties["uart_speed_mode"] + " Parity: " + device_properties["uart_parity_mode"];
        	break;
        }
        case "wd": {
            main_el = document.createElement("h1");
            var enabled_text = "";
            if (device_properties["value"] == 1) {
            	enabled_text = "Enabled"
            } else {
            	enabled_text = "Disabled"
            }
            if (device_properties["watchdog_was_wd_reset"] == 0) {
            	main_el.textContent = enabled_text + " [Not Triggered]";
            } else {
            	main_el.textContent = enabled_text + " [Triggered]";
            }
            wd_device_cache.push(circuit);
        	break;
        }
        case "wifi": {
        	main_el = document.createElement("h1");
        	main_el.textContent = device_properties["wifi_ap_state"];
        	break;
        }
        case "light_channel": {
            main_el = document.createElement("input");
            main_el.className = "out";
            main_el.min = 0;
            main_el.step = 1.0;
            main_el.max = 254;
        	break;
        }
        default: {
            main_el = document.createElement("h1");
            main_el.innerHTML = device_properties["value"] + " " + device_properties["unit"];
            break;
        }
        }

        main_el.id = device_signature + "_value";


        //Create label
        label = document.createElement("label");
        label.id = device_signature + "_label";
        label.setAttribute("for", main_el.id);
        label.innerHTML = device_properties["device_name"];

        //Create the div structure
        div.appendChild(label);
        if (device == "ao" || device == "light_channel") { 
        	div.appendChild(main_el);
        } else {
        	div.appendChild(right_div); 
        	right_div.appendChild(main_el);
        }
        li.appendChild(div);

        //And append it to the html
        switch(device) {
        case "ai": {
            var divider = document.getElementById("unipi_temp_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        	break;
        }
        case "ao": {
            $('#outputs_list').append(li);
            $('#' + main_el.id).slider();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("slidestop", function (event, ui) {
                makePostRequest('ao/' + circuit, 'value=' + $(this).val());
            });

        	break;
        }
        case "led": {
            var divider = document.getElementById("unipi_ao_divider");
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('led/' + circuit, 'value=' + $(this).val());
            });
        	break;
        }
        case "relay": {
            var divider = document.getElementById("unipi_led_divider");
        	if (("relay_type" in msg) && msg.relay_type == "digital") {
        		divider = document.getElementById("unipi_relay_divider");
        	} 
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).flipswitch();
            $('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("change", function (event, ui) {
            	$.postJSON('relay/' + circuit, {value: $(this).val})
            });
        	break;       	
        }
        case "input": {
            var divider = document.getElementById("unipi_ai_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        	break;        	
        }
        case "1wdevice": {}
        case "temp": {
            var divider = document.getElementById("unipi_modbus_divider");
            var list = document.getElementById("inputs_list");
            list.insertBefore(li, divider);
            $('#inputs_list').listview('refresh');
        	break;       	
        }
        case "unit_register": {
            $('#inputs_list').append(li);
            $('#inputs_list').listview('refresh');
        	break;       	
        }
        case "device_info": {
            var divider = document.getElementById("unipi_watchdog_divider");
            var list = document.getElementById("system_list");
            list.insertBefore(li, divider);
            $('#system_list').listview('refresh');
        	break;        	
        }
        case "modbus_slave": {
            $('#system_list').append(li);
            $('#system_list').listview('refresh');
        	break;
        }
        case "wd": {
            var divider = document.getElementById("unipi_modbus_slave_divider");
            var list = document.getElementById("system_list");
            list.insertBefore(li, divider);
        	$('#system_list').listview('refresh');
        	break;        	
        }
        case "light_channel": {
        	var divider = document.getElementById("unipi_digital_divider");
        	$("#unipi_light_channel_divider").css("display", "block");
            var list = document.getElementById("outputs_list");
            list.insertBefore(li, divider);
            $('#' + main_el.id).slider();
        	$('#outputs_list').listview('refresh');
            $('#' + main_el.id).bind("slidestop", function (event, ui) {
                makePostRequest('light_channel/' + circuit, 'broadcast_command=DAPC&broadcast_argument=' + $(this).val());
            });
            $("#" + device_signature + "_value").val(0).slider("refresh");
        	break;        	
        }
        }
    // Device representation already exists 
    } else if (device != 'register' && device != 'owbus') {
        var main_el = document.getElementById(device_signature + "_value");
        var label = document.getElementById(device_signature + "_label");
        label.innerHTML = device_properties["device_name"];
        // Set device-specific data
        switch(device) {
        case "relay": {
            //unbind to prevent looping
        	$('#' + main_el.id).unbind("change");
            $("#" + device_signature + "_value").val(device_properties["value"]).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('relay/' + circuit, 'value=' + $(this).val());
            });
            break;
        }
        case "led": {
            //unbind to prevent looping
            $('#' + main_el.id).unbind("change");
            $("#" + device_signature + "_value").val(device_properties["value"]).flipswitch("refresh");
            //and bind again
            $('#' + main_el.id).bind("change", function (event, ui) {
                makePostRequest('led/' + circuit, 'value=' + $(this).val());
            });
            break;
        }
        case "ao": {
            $("#" + device_signature + "_value").val(device_properties["value"]).slider("refresh");
            break;
        }
        case "input": {
            if (msg.counter_mode != "Disabled") {
                var counter_el = document.getElementById(device_signature + "_counter");
                //counter_el.innerHTML = counter;
            }
            if ("bitvalue" in device_properties) {
            	main_el.innerHTML = (device_properties["bitvalue"] == 1) ? "On" : "Off";
            } else {
            	main_el.innerHTML = (device_properties["value"] == 1) ? "On" : "Off";        	
            }
            break;
        }
        case "1wdevice": {
        	if (device_properties["typ"] == "DS2438") {
            	main_el.innerHTML = "" + device_properties["humidity"] + " %<br>" + device_properties["value"] + " " + device_properties["unit"];            		
        	}
        	break;
        }
        case "device_info": {
            if (device_properties["device_info_sn"] != null) {
            	main_el.innerHTML = "S/N: " + device_properties["device_info_sn"];
            } else {
            	main_el.innerHTML = "";
            }
            break;
        }
        case "modbus_slave": {
            main_el.innerHTML = "Address: " + device_properties["device_slave_id"];
            break;
        }
        case "uart": {
        	main_el.innerHTML  = "Speed: " + device_properties["uart_speed_mode"] + " Parity: " + device_properties["uart_parity_mode"];
        	break;
        }
        case "wd": {
            var enabled_text = "";
            if (device_properties["value"] == 1) {
            	enabled_text = "Enabled"
            } else {
            	enabled_text = "Disabled"
            }
            if (device_properties["watchdog_was_wd_reset"] == 0) {
            	main_el.innerHTML = enabled_text + " [Not Triggered]";
            } else {
            	main_el.innerHTML = enabled_text + " [Triggered]";
            }        	
            break;
        }
        case "wifi": {
        	main_el.innerHTML = device_properties["wifi_ap_state"];
        	break;
        }
        case "light_channel": {
        	//main_el.innerHTML = "Channel " + circuit;
        	break;
        }       
        default: {
            main_el.innerHTML = device_properties["value"] + " " + device_properties["unit"];
            break;
        }
        }
    } 
}

function updateValues() {
	if (legacy_api) {
	    $.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/all',
	        dataType: 'json',
	        success: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'hidden');
	            data = sortResults(data);
	            $.each(data, function (name, msg) {
                        syncDevice(msg);
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
	                syncDevice(msg);
	            });
	        },
	        error: function (data) {
				$("#unipi_loading_spinner").css('visibility', 'visible');
	        }
	    });    	
    }
}

function configButtonHandler(event) {
	var $this = $(this);
	var device = event.currentTarget.href.substr(
			(event.currentTarget.href.length - (event.currentTarget.hash.length - 1)), 
			(event.currentTarget.href.length)
		);
	var circuit = event.currentTarget.id.substr(30 + device.length, (event.currentTarget.id.length));
	event.preventDefault();
    var circuit_display_name = circuit.replace(/\_/g, ' ');
    if (circuit_display_name.substring(circuit_display_name.length - 3,circuit_display_name.length - 2) == ' ') {
    	circuit_display_name = circuit_display_name.substring(0,circuit_display_name.length - 3) + '.' + circuit_display_name.substring(circuit_display_name.length - 2, circuit_display_name.length);
    }
	var config_device_header = $("<h3>", {id: "config_form_device_header"});
	config_device_header.text(getConfigurationFormTitle(device));
	var config_circuit_header = $("<h5>", {id: "config_form_circuit_header"});
	if (device != "device_info") {
		config_circuit_header.text(circuit_display_name);
	} else {
		config_circuit_header.text("PLC Device: " + circuit_display_name);
	}
	$("#unipi_config_form_inner_div").empty();
	$("#unipi_config_form_inner_div").append(config_device_header);
	$("#unipi_config_form_inner_div").append(config_circuit_header);
    $.ajax({
    	crossDomain: true,
    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + '/rest/' + device + '/' + circuit + '/',
        dataType: 'json',
        success: function (data) {
            configButtonRestSuccessCallback(data);
        },
        error: function (data) {
        	configButtonRestFailureCallback(data);
        }
    });
}

function configButtonRestSuccessCallback(data) {
	var device = data.dev;
	var circuit = data.circuit;
	populateConfigForm($("#unipi_config_form_inner_div"), device, circuit, data);
	$("#unipi_config_form_div").popup("open");
}

function configButtonRestFailureCallback(data) {
	$("#unipi_config_form_device_field").val("suppress");
	$("#unipi_config_form_div").popup("close");
}


$(document).ready(function(){
	$("#unipi_save_all_button").on("click", function(event) {saveAllButtonHandler(event);});
});

function saveAllButtonHandler(event) {
	event.preventDefault();
	$.each(wd_device_cache, function(index, value) {
		$.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + "/rest/wd/" + value + '/',
	        type: 'POST',
	        data: {"nv_save": 1},
	        success: function (data) {
	        },
	        error: function (data) {
	        	alert("Error saving data: " + data.errors);
	        }
	    });
	});
	
}

function createConfigPostRequestDict(arg_fields) {
	var outp = {};
	for (var i = 0; i < arg_fields.length; i++) {
		switch(arg_fields[i].id) {
		case "unipi_config_form_mode_select_field": {
			outp["mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_range_select_field": {
			outp["range"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_alias_field": {
			if (arg_fields[i].value != "") {
				var encoded_alias = arg_fields[i].value.replace(/ /g,"_");
				outp["alias"] = encoded_alias;
			} else {
				outp["alias"] = "";
			}
			break;
		}
		case "unipi_config_form_pwm_freq_field": {
			outp["pwm_freq"] = parseFloat(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_pwm_duty_field": {
			outp["pwm_duty"] = parseFloat(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_debounce_field": {
			outp["debounce"] = parseFloat(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_counter_field": {
			outp["counter"] = parseFloat(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_counter_mode_select_field": {
			outp["counter_mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_ds_mode_select_field": {
			outp["ds_mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_parity_mode_select_field": {
			outp["parity_mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_stopb_mode_select_field": {
			outp["stopb_mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_speed_mode_select_field": {
			outp["speed_mode"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_enabled_select_field": {
			outp["value"] = parseInt(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_timeout_field": {
			outp["timeout"] = parseInt(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_nv_save_select_field": {
			outp["nv_save"] = parseInt(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_wd_reset_select_field": {
			outp["reset"] = parseInt(arg_fields[i].value);
			break;
		}
		case "unipi_config_form_ap_state_select_field": {
			outp["ap_state"] = arg_fields[i].value;
			break;
		}
		case "unipi_config_form_eth0_masq_select_field": {
			outp["eth0_masq"] = arg_fields[i].value;
			break;
		}
		default: {
			break;
		}
		}
	}
	return outp;
}

function configFormSubmitHandler(event) {
	if ($("#unipi_config_form_device_field").val() == "device_info") {
		var circuit = $("#unipi_config_form_circuit_field").val();
		var device = $("#unipi_config_form_device_field").val();
		event.preventDefault();
		$("#unipi_config_form_device_field").val("suppress");
		$("#unipi_config_form_div").popup("close");
		$.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + "/rest/device_info/" + circuit + '/',
	        type: 'POST',
	        data: {"print_log": 1},
	        success: function (data) {
	        	if (data.result == "") {
		        	alert("EVOK log is empty");
	        	} else {
		        	alert(data.result);
	        	}
	        },
	        error: function (data) {
	        }
	    });
	} else if ($("#unipi_config_form_device_field").val() == "suppress") {
		return false;
	} else {
		var circuit = $("#unipi_config_form_circuit_field").val();
		var device = $("#unipi_config_form_device_field").val();
		event.preventDefault();
		$("#unipi_config_form_device_field").val("suppress");
		$("#unipi_config_form_div").popup("close");
		var post_request_dict = createConfigPostRequestDict(event.originalEvent.target.elements);
		$.ajax({
	    	crossDomain: true,
	    	url: 'http://' + $(location).attr('hostname') + ':' + api_port + "/rest/" + device + "/" + circuit + '/',
	        type: 'POST',
	        data: post_request_dict,
	        success: function (data) {
	        	if (data.success) {
	        		updateValues();
	        		if ("alias" in post_request_dict) {
	        			if (post_request_dict["alias"] == "") {
	        			    var circuit_display_name = circuit.replace(/\_/g, ' ');
	        			    if (circuit_display_name.substring(circuit_display_name.length - 3,circuit_display_name.length - 2) == ' ') {
	        			    	circuit_display_name = circuit_display_name.substring(0,circuit_display_name.length - 3) + '.' + circuit_display_name.substring(circuit_display_name.length - 2, circuit_display_name.length);
	        			    }
	        				$("#unipi_config_div_grid_anchor_" + device + "_" + circuit).text(circuit_display_name);
	        			} else {
	        				var decoded_alias = post_request_dict["alias"];
	        				decoded_alias = decoded_alias.replace(/_/g," ");
	        				$("#unipi_config_div_grid_anchor_" + device + "_" + circuit).text(decoded_alias);
	        			}
	        		}
	        	} else {
	        		alert("Operation failed with the following error: " + data.errors["__all__"]);
	        	}
	        },
	        error: function (data) {
	        	alert("Operation failed with the following error: " + data.message);
	        }
	    });
	}
}

function webSocketRegister() {
    if ("WebSocket" in window) {
        if (ws) {
            return;
        }
        var loc = window.location;
        uri = ((loc.protocol === "https:") ? "wss://" : "ws://") + loc.hostname + ':' + api_port;

        ws = new WebSocket(uri + "/ws");
        
        if (!ws) {
            setTimeout(webSocketRegister, 1000);
            return;
        }
        
        window.onbeforeunload = function () {
            ws.onclose = function () {
            }; 
            ws.close()
        };

        ws.onopen = function () {
            updateValues();
        };

        ws.onmessage = function (evt) {
            var received_msg = evt.data;
            var msg = JSON.parse(evt.data);
			$("#unipi_loading_spinner").css('visibility', 'hidden');
            if (msg.constructor === Array) {
                data = sortResults(msg);
                $.each(data, function (name, msg) {
                    syncDevice(msg);
                });
            } else {
                syncDevice(msg);
            }
        };

        ws.onclose = function () {
            setTimeout(webSocketRegister, 1000);
            ws = null;
        };
		
		ws.onerror = function () {
			$("#unipi_loading_spinner").css('visibility', 'visible');
		};
    }
    else {
        alert("YOUR BROWSER DOES NOT HAVE WEBSOCKET SUPPORT!");
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

