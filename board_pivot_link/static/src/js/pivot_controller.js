odoo.define('board_pivot_link.PivotController', function (require) {
"use strict";

var PivotController = require('web.PivotController');

return PivotController.include({
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.boardControllerID = params.boardControllerID || false;
    },
});

})