from odoo import models, _


class VatReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_reports_buttons(self):
        res = super()._get_reports_buttons()
        res.append({'name': _('Auditor Report'), 'sequence': 3, 'action': 'l10n_cy_print_xlsx',
                     'file_export_type': _('XLSX')})
        return res

    def l10n_cy_print_xlsx(self, options):
        # add options to context and return action to open transient model
        ctx = self.env.context.copy()
        ctx['vat_report_wizard'] = options
        new_wizard = self.env['vat_report_wizard'].create({})
        view_id = self.env.ref('vat_report.view_account_financial_report_export').id
        return {
            'name': _('XLSX Export Options'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'vat_report_wizard',
            'type': 'ir.actions.act_window',
            'res_id': new_wizard.id,
            'target': 'new',
            'context': ctx,
            }
