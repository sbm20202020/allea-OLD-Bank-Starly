odoo.define('board_pivot_link.PivotView', function (require) {
"use strict";

var PivotView = require('web.PivotView');

return PivotView.include({

    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.controllerParams.boardControllerID = params.boardControllerID;
    },

})

});