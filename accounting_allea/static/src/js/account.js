odoo.define('account_icode.account', function(require) {
    "use strict";
var core = require('web.core');
var Widget = require('web.Widget');
var crash_manager = require('web.crash_manager');
var datepicker = require('web.datepicker');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;
// var core = require('web.core');
var Widget = require('web.Widget');
// var ControlPanelMixin = require('web.ControlPanelMixin');
var accountReportsWidget = require('account_icode.accountReportsWidget');


    console.log('20180927.');

var accountReportsWidget = Widget.extend(ControlPanelMixin, {

        init: function(parent) {
        this._super.apply(this, arguments);
        },


        render_searchview_buttons: function() {
        var self = this;
        // bind searchview buttons/filter to the correct actions
        var $datetimepickers = this.$searchview_buttons.find('.js_account_reports_datetimepicker');
        var options = { // Set the options for the datetimepickers
            locale : moment.locale(),
            format : 'L',
            icons: {
                date: "fa fa-calendar",
            },
        };
        // attach datepicker
        $datetimepickers.each(function () {
            $(this).datetimepicker(options);
            var dt = new datepicker.DateWidget(options);
            dt.replace($(this));
            dt.$el.find('input').attr('name', $(this).find('input').attr('name'));
            if($(this).data('default-value')) { // Set its default value if there is one
                dt.setValue(moment($(this).data('default-value')));
            }
        });
        // format date that needs to be show in user lang
        _.each(this.$searchview_buttons.find('.js_format_date'), function(dt) {
            var date_value = $(dt).html();
            $(dt).html((new moment(date_value)).format('ll'));
        });
        // fold all menu
        this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu o_open_menu');
        });
        // render filter (add selected class to the options that are selected)
        _.each(self.report_options, function(k) {
            if (k!== null && k.filter !== undefined) {
                self.$searchview_buttons.find('[data-filter="'+k.filter+'"]').addClass('selected');
            }
        });
        _.each(this.$searchview_buttons.find('.js_account_report_bool_filter'), function(k) {
            $(k).toggleClass('selected', self.report_options[$(k).data('filter')]);
        });
        _.each(this.$searchview_buttons.find('.js_account_report_choice_filter'), function(k) {
            $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
        });
        _.each(this.$searchview_buttons.find('.js_account_reports_one_choice_filter'), function(k) {
            $(k).toggleClass('selected', ''+self.report_options[$(k).data('filter')] === ''+$(k).data('id'));
        });
        // click event
        this.$searchview_buttons.find('.js_account_report_date_filter').click(function (event) {
            self.report_options.date.filter = $(this).data('filter');
            var error = false;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                if (date_from.length > 0){
                    error = date_from.val() === "" || date_to.val() === "";
                    self.report_options.date.date_from = field_utils.parse.date(date_from.val());
                    self.report_options.date.date_to = field_utils.parse.date(date_to.val());
                }
                else {
                    error = date_to.val() === "";
                    self.report_options.date.date = field_utils.parse.date(date_to.val());
                }
            }
            if (error) {
                crash_manager.show_warning({data: {message: _t('Date cannot be empty')}});
            } else {
                self.reload();
            }
        });
        this.$searchview_buttons.find('.js_account_report_bool_filter').click(function (event) {
            var option_value = $(this).data('filter');
            self.report_options[option_value] = !self.report_options[option_value];
            if (option_value === 'unfold_all') {
                self.unfold_all(self.report_options[option_value]);
            }
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_report_choice_filter').click(function (event) {
            var option_value = $(this).data('filter');
            var option_id = $(this).data('id');
            _.filter(self.report_options[option_value], function(el) {
                if (''+el.id == ''+option_id){
                    if (el.selected === undefined || el.selected === null){el.selected = false;}
                    el.selected = !el.selected;
                }
                return el;
            });
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_reports_one_choice_filter').click(function (event) {
            self.report_options[$(this).data('filter')] = $(this).data('id');
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_report_date_cmp_filter').click(function (event){
            self.report_options.comparison.filter = $(this).data('filter');
            var error = false;
            var number_period = $(this).parent().find('input[name="periods_number"]');
            self.report_options.comparison.number_period = (number_period.length > 0) ? parseInt(number_period.val()) : 1;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from_cmp"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to_cmp"]');
                if (date_from.length > 0){
                    error = date_from.val() === "" || date_to.val() === "";
                    self.report_options.comparison.date_from = field_utils.parse.date(date_from.val());
                    self.report_options.comparison.date_to = field_utils.parse.date(date_to.val());
                }
                else {
                    error = date_to.val() === "";
                    self.report_options.comparison.date = field_utils.parse.date(date_to.val());
                }
            }
            if (error) {
                crash_manager.show_warning({data: {message: _t('Date cannot be empty')}});
            } else {
                self.reload();
            }
        });
        // analytic filter
        this.$searchview_buttons.find('.js_account_reports_analytic_auto_complete').select2();
        if (self.report_options.analytic) {
            self.$searchview_buttons.find('[data-filter="analytic_accounts"]').select2("val", self.report_options.analytic_accounts);
            self.$searchview_buttons.find('[data-filter="analytic_tags"]').select2("val", self.report_options.analytic_tags);
            // icode Ruzki
            self.$searchview_buttons.find('[data-filter="chart_accounts"]').select2("val", self.report_options.chart_accounts);
        }
        this.$searchview_buttons.find('.js_account_reports_analytic_auto_complete').on('change', function(){
            self.report_options.analytic_accounts = self.$searchview_buttons.find('[data-filter="analytic_accounts"]').val();
            self.report_options.analytic_tags = self.$searchview_buttons.find('[data-filter="analytic_tags"]').val();
            // icode Ruzki
            self.report_options.chart_accounts = self.$searchview_buttons.find('[data-filter="chart_accounts"]').val();
            return self.reload().then(function(){
                self.$searchview_buttons.find('.account_analytic_filter').click();
            })
        });
    },

    });

});




