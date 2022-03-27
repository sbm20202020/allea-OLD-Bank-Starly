from odoo import models, api  # noqa: F401 #pylint: disable=W0611


class AccountMove(models.Model):
    """AccountMove"""

    _inherit = 'account.move'

    def write(self, values):
        result = super().write(values)
        line_ids = values.get('line_ids')
        if line_ids:
            for line in line_ids:
                line_type = line[0]
                if line_type == 1:
                    line_val = line[2]
                    if line_val:
                        line_an_acc_id = line_val.get('analytic_account_id', False)
                        aml_id = line[1]
                        aml = self.env['account.move.line'].browse(aml_id)
                        if aml:
                            aml.write({'analytic_account_id': line_an_acc_id})
                            aml.create_analytic_lines()
        return result
