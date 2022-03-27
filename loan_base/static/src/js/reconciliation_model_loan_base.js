odoo.define('account.ReconciliationModel.loan_base', function (require) {
    "use strict";
    var field_utils = require('web.field_utils');

    var account_reconciliation_model = require('account.ReconciliationModel').StatementModel;
    account_reconciliation_model.include({
        // _loadLoans: function(){
        //     var self = this;
        //     self.loans = {};
        //     return this._rpc({
        //         model: 'account.loan.agreement',
        //         method: 'search_read',
        //         fields: ['price_include', 'amount_type'],
        //     }).then(function (loans) {
        //         _.each(loans, function(loan){
        //             self.loans[loan.id] = {
        //                 price_include: loan.price_include,
        //                 amount_type: loan.amount_type,
        //             }
        //         })
        //     });
        // },
        quickCreateProposition: function (handle, reconcileModelId) {
            var line = this.getLine(handle);
            var reconcileModel = _.find(this.reconcileModels, function (r) {
                return r.id === reconcileModelId;
            });
            var fields = ['account_id', 'amount', 'amount_type', 'analytic_account_id', 'journal_id', 'label', 'force_tax_included', 'tax_id', 'analytic_tag_ids', 'name', 'match_loan_id'];
            this._blurProposition(handle);
            debugger;
            var focus = this._formatQuickCreate(line, _.pick(reconcileModel, fields));
            focus.reconcileModelId = reconcileModelId;
            line.reconciliation_proposition.push(focus);

            if (reconcileModel.has_second_line) {
                var second = {};
                _.each(fields, function (key) {
                    second[key] = ("second_" + key) in reconcileModel ? reconcileModel["second_" + key] : reconcileModel[key];
                });
                focus = this._formatQuickCreate(line, second);
                focus.reconcileModelId = reconcileModelId;
                line.reconciliation_proposition.push(focus);
                this._computeReconcileModels(handle, reconcileModelId);
            }
            line.createForm = _.pick(focus, this.quickCreateFields);
            return this._computeLine(line);
        },

        _formatQuickCreate: function (line, values) {
            values = values || {};
            var today = new moment().utc().format();
            var account = this._formatNameGet(values.account_id);
            var formatOptions = {
                currency_id: line.st_line.currency_id,
            };
            var amount = values.amount !== undefined ? values.amount : line.balance.amount;
            var base_amount;
            var percent;
            if (values.amount_type === "percentage") {
                base_amount = line.balance.amount * values.amount / 100;
                percent = values.amount;
            } else {
                base_amount = amount;
                percent = null;
            }
            console.log('line=');
            console.log(line);
            console.log('values=');
            console.log(values);
            console.log('match_loan_id=');
            console.log(values.match_loan_id);
            debugger;
            var prop = {
                'id': _.uniqueId('createLine'),
                'label': values.label || line.st_line.name,
                'account_id': account,
                'account_code': account ? this.accounts[account.id] : '',
                'analytic_account_id': this._formatNameGet(values.analytic_account_id),
                // 'analytic_tag_ids': this._formatMany2ManyTags(values.analytic_tag_ids || []),
                'journal_id': this._formatNameGet(values.journal_id),
                'tax_id': this._formatNameGet(values.tax_id),
                'debit': 0,
                'credit': 0,
                'date': values.date ? values.date : field_utils.parse.date(today, {}, {isUTC: true}),
                'base_amount': base_amount,
                'percent': percent,
                'link': values.link,
                'display': true,
                'invalid': true,
                '__tax_to_recompute': true,
                'is_tax': values.is_tax,
                '__focus': '__focus' in values ? values.__focus : true,
                'loan_account_id': values.match_loan_id,
            };
            if (prop.base_amount) {
                // Call to format and parse needed to round the value to the currency precision
                var sign = prop.base_amount < 0 ? -1 : 1;
                var amount = field_utils.format.monetary(Math.abs(prop.base_amount), {}, formatOptions);
                prop.base_amount = sign * field_utils.parse.monetary(amount, {}, formatOptions);
            }

            if (prop.tax_id) {
                // Set the amount_type value.
                prop.tax_id.amount_type = this.taxes[prop.tax_id.id].amount_type;
                // Set the price_include value.
                prop.tax_id.price_include = this.taxes[prop.tax_id.id].price_include;
            }

            // Set the force_tax_included value.
            if (prop.tax_id && values.force_tax_included !== undefined)
                prop.force_tax_included = values.force_tax_included;
            else if (prop.tax_id && this.taxes[prop.tax_id.id].price_include)
                prop.force_tax_included = this.taxes[prop.tax_id.id].price_include;
            prop.amount = prop.base_amount;
            return prop;
        }
    });


});
