var config_order = ["main", "gpiobus", "owbus", "i2cbus", "eprom", "mcp", "aichip", "pca9685", "sensor", "1wdevice", "relay", "1wrelay", "ao", "di", "1winput"];
var current_config = {};
var current_config_index = null;

/**
 * Get config via HTTP get request and call syncConfig()
 */
function get_config() {
    $.get("/config")
        .done(function( data ) {
            syncConfig(data);
        });
}

/**
 * get Device from config array and store its position
 */
function getDevFromCfg(devtype, circuit){
    return $.grep(current_config, function(item, index){
        if (typeof circuit === 'undefined' || circuit === null || circuit == '') {
            if (item.devtype == devtype) {
                current_config_index = index;
                return item;
            }
        }
        else {
            if (item.devtype == devtype && item.circuit == circuit) {
                current_config_index = index;
                return item;
            }
        }
    })[0];
}


/**
 * Parse current_config to evok.conf and upload it
 * evok should take care of save & restart the service
 */
function uploadConfig(){
    var conf = {};
    $.each(current_config, function(i,row) {
        obj = {};
        content = {};
        //add object name
        var objname = row.devtype.toUpperCase();
        if (typeof(row.circuit) !== 'undefined') {
            objname+='_'+row.circuit;
        }
        //and fill out all attributes
        for (attr in row) {
            if (attr != 'devtype' && attr != 'circuit') {
                content[attr] = row[attr];
            }
        }
        conf[objname]=content;
    });
    //and post config to evok
    $.post("/config", JSON.stringify(conf));
    //TODO!!!
    $.mobile.loading( "show", {
        text: "Applying configuration... ",
        textVisible: true,
        textonly: false
    });
    //redirect to new page
    var arr = window.location.href.split("/");
    var url = arr[0]+"//"+arr[2]+":"+current_config[0].port+"/"+arr[3];
    setTimeout(function(){ window.location = url; $.mobile.loading("hide");}, 3000);
}


/**
 * Conevert received config (python's configparser syntax) and convert it to array readable by jquery tmpl
 */
function confToTMPL(conf) {
    var tmp = [];
    var template_arr = [];
    for (dev in conf){
        var obj = {}
        obj.devtype = dev.split("_")[0].toLocaleLowerCase();
        if (obj.devtype != "main") {
            //skip adding 'circuit' to the main config section
            obj.circuit = dev.split("_")[1];
        }
        //if (typeof obj.circuit === "undefined") {obj.circuit=null;}
        $.extend(obj, conf[dev]);
        tmp.push(obj);
    }
    return sortArrayConfig(tmp);
}

function sortArrayConfig(conf) {
    var conf_arr = [];
    for (dev in config_order) {
        //grep array by config_order
        var arr = $.grep(conf, function(n,i) {
            return n.devtype == config_order[dev];}
        );
        //skip empty/non-existing devices
        if (arr.length == 0) {continue;}
        //and sort sub-array
        arr.sort(function(a,b){
            return a.circuit - b.circuit;
        });
        $.merge(conf_arr,arr);
    }
    return conf_arr;
}

/**
 * Read config and also render elements using templates
 */
function syncConfig(conf) {
    //preload config from json to array
    if (typeof  conf != 'undefined') {
        var config = confToTMPL(conf);
        current_config = config;
    }
    //othervise just refresh all devices
    $("#div_devices_container").empty();
    $("#template-edit-device-button").tmpl(current_config).appendTo("#div_devices_container");
}

/**
 * Load currently edited device into template
 */
function loadEditPageData(devtype, circuit) {
    var currdev = getDevFromCfg(devtype,circuit);
    $.each(currdev, function(key, value) {
        if (key == 'devtype') {
            return;
        }
        var el = $('*[data-edit="' + currdev.devtype + '"][data-save="'+key+'"]');
        setElementValue(el, value);
    });
}

/**
 * Set element value on the device edit page
 */
function setElementValue(el, value) {
    switch (el.get(0).tagName) {
        case "SELECT":
            el.selectmenu();
            el.val(value).selectmenu('refresh');
            break;
        case "INPUT":
            el.val(value);
            break;
    }
}

/**
 * Get value of element on the device edit page
 */
function getElementValue(el) {
    switch ($(el).get(0).tagName) {
        case "SELECT":
        case "INPUT":
            return $(el).val();
    }
}

/**
 * Save currently editing device to the config
 * also takes car of updating/adding new devices
 */
function saveConfig(devtype){
    var obj = {};
    obj.devtype = devtype;
    //iterate over each input element and get its value
    $.each($('*[data-edit="'+devtype+'"]'), function(i, el) {
        var param = $(this).data().save;
        obj[param] = getElementValue(el);
    });

    if (current_config_index == null) {
        //add a new device and sort array
        current_config.push(obj);
        current_config = sortArrayConfig(current_config);
    }
    else {
        current_config[current_config_index] = obj;
    }
    syncConfig();
    current_config_index = null;
    window.location.href = '#page-settings';
    return false;
}

/**
 * Check both input fields for new password
 * ane enable apply button if not empty and match
 */
function CheckNewSshPassword() {
    var p1 = $('#edit_ssh_password').val();
    var p2 = $('#edit_retype_ssh_password').val();
    if (p1 != '' && p1 == p2) {
        $('#ssh_password_save_btn').prop("disabled",false);
    }
    else {
        $('#ssh_password_save_btn').prop("disabled",true);
    }
}

/**
 * Call evok api
 */
function setNewPassword() {
    var pw = $('#edit_ssh_password').val();
    callRemoteCMD('pw',pw);
}

/**
 * Call evok api
 */
function callRemoteCMD(service,status) {
    $.mobile.loading( "show", {
        text: "Loading...",
        textVisible: true,
        textonly: false
    });
    $.post("/config/cmd", {
        'service':service,
        'status':status
        },
        function() {
            $.mobile.loading("hide");
        });
}