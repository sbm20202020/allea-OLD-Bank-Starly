odoo.define('account.ReconciliationModel.loan_base', function (require) {
    "use strict";
    var field_utils = require('web.field_utils');

    var account_reconciliation_model = require('account.ReconciliationModel').StatementModel;
    account_reconciliation_model.include({
        /**
         * helper function
         */
        getPrincipalInterest: function (ids) {
            var self = this;
            return this._rpc({
                model: 'account.bank.statement.line',
                method: 'get_principal_interest',
                args: [ids]
            });
        },

        /**
         * Apply default values for the proposition, format datas and format the
         * base_amount with the decimal number from the currency
         *
         * @private
         * @param {Object} line
         * @param {Object} values
         * @returns {Object}
         */
        _formatQuickCreate: function (line, values) {
            values = values || {};
            var account = this._formatNameGet(values.account_id);
            var formatOptions = {
                currency_id: line.st_line.currency_id
            };
            var amount = values.amount !== undefined ? values.amount : line.balance.amount;
            var prop = {
                'id': _.uniqueId('createLine'),
                'label': values.label || line.st_line.name,
                'account_id': account,
                'account_code': account ? this.accounts[account.id] : '',
                'analytic_account_id': this._formatNameGet(values.analytic_account_id),
                'journal_id': this._formatNameGet(values.journal_id),
                'tax_id': this._formatNameGet(values.tax_id),
                'debit': 0,
                'credit': 0,
                'base_amount': values.amount_type !== "percentage" ?
                    (amount) : line.balance.amount * values.amount / 100,
                'percent': values.amount_type === "percentage" ? values.amount : null,
                'link': values.link,
                'display': true,
                'invalid': true,
                '__tax_to_recompute': true,
                'is_tax': values.is_tax,
                '__focus': '__focus' in values ? values.__focus : true,
                'loan_agreement_id': line.st_line.loan_agreement_id || 0
            };
            if (prop.base_amount) {
                // Call to format and parse needed to round the value to the currency precision
                var sign = prop.base_amount < 0 ? -1 : 1;
                amount = field_utils.format.monetary(Math.abs(prop.base_amount), {}, formatOptions);
                prop.base_amount = sign * field_utils.parse.monetary(amount, {}, formatOptions);
            }
            prop.amount = prop.base_amount;
            return prop;
        },
        /**
         * Add lines into the propositions from the reconcile model
         * Can add 2 lines, and each with its taxes. The second line become editable
         * in the create mode.
         *
         * @see 'updateProposition' method for more informations about the
         * 'amount_type'
         *
         * @param {string} handle
         * @param {integer} reconcileModelId
         * @returns {Deferred}
         */
        quickCreateProposition: function (handle, reconcileModelId) {
            var line = this.getLine(handle);
            var reconcileModel = _.find(this.reconcileModels, function (r) {
                return r.id === reconcileModelId;
            });
            var fields = ['account_id', 'amount', 'amount_type', 'analytic_account_id', 'journal_id', 'label', 'tax_id'];
            this._blurProposition(handle);

            var focus = this._formatQuickCreate(line, _.pick(reconcileModel, fields));
            var self = this;
            var my_result = this.getPrincipalInterest(line.id);
            return $.when(my_result).then(function (result) {
                if (result.is_loan) {
                    focus.amount = result.interest;
                    focus.account_id = result.interest_account_id;
                    focus.account_code = result.interest_account_code;
                }
                focus.reconcileModelId = reconcileModelId;

                line.reconciliation_proposition.push(focus);

                if (reconcileModel.has_second_line) {
                    var second = {};
                    _.each(fields, function (key) {
                        second[key] = ("second_" + key) in reconcileModel ? reconcileModel["second_" + key] : reconcileModel[key];
                    });
                    focus = self._formatQuickCreate(line, second);
                    if (result.is_loan) {
                        focus.amount = result.principal;
                        focus.account_id = result.principal_account_id;
                        focus.account_code = result.principal_account_code;
                    }
                    focus.reconcileModelId = reconcileModelId;
                    line.reconciliation_proposition.push(focus);
                    self._computeReconcileModels(handle, reconcileModelId);
                }
                line.createForm = _.pick(focus, this.quickCreateFields);
                return self._computeLine(line);
            });
        }
    });
});
