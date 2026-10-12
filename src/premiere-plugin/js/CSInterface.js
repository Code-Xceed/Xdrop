/**
 * CSInterface - v11.0.0
 * Adobe Common Extensibility Platform (CEP) Interface
 */

function CSInterface() {
    this.hostEnvironment = null;
}

/**
 * User Colors
 */
CSInterface.THEME_COLOR_CHANGED_EVENT = "com.adobe.csxs.events.ThemeColorChanged";

/**
 * Evaluates JavaScript code in the ExtendScript context.
 *
 * @param script The JavaScript code string to evaluate.
 * @param callback Optional. The callback function that receives the evaluation result.
 */
CSInterface.prototype.evalScript = function(script, callback) {
    if (window.__adobe_cep__) {
        window.__adobe_cep__.evalScript(script, callback || function() {});
    } else {
        if (callback) callback("ERR_NO_CEP");
    }
};

/**
 * Retrieves the host environment data.
 */
CSInterface.prototype.getHostEnvironment = function() {
    if (window.__adobe_cep__) {
        this.hostEnvironment = JSON.parse(window.__adobe_cep__.getHostEnvironment());
        return this.hostEnvironment;
    }
    return null;
};

/**
 * Registers an event listener.
 */
CSInterface.prototype.addEventListener = function(type, listener, obj) {
    if (window.__adobe_cep__) {
        window.__adobe_cep__.addEventListener(type, listener, obj);
    }
};

/**
 * Removes an event listener.
 */
CSInterface.prototype.removeEventListener = function(type, listener, obj) {
    if (window.__adobe_cep__) {
        window.__adobe_cep__.removeEventListener(type, listener, obj);
    }
};

/**
 * Dispatches a CEP event.
 */
CSInterface.prototype.dispatchEvent = function(event) {
    if (window.__adobe_cep__) {
        window.__adobe_cep__.dispatchEvent(event);
    }
};

/**
 * Opens a page in the default web browser.
 */
CSInterface.prototype.openURLInDefaultBrowser = function(url) {
    if (window.__adobe_cep__) {
        cep.util.openURLInDefaultBrowser(url);
    } else {
        window.open(url, "_blank");
    }
};

/**
 * Closes this extension window.
 */
CSInterface.prototype.closeExtension = function() {
    if (window.__adobe_cep__) {
        window.__adobe_cep__.closeExtension();
    }
};

if (typeof module !== 'undefined') {
    module.exports = CSInterface;
}
