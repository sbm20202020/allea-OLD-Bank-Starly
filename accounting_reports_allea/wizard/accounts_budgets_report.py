import base64

from odoo import models, fields
import io
import pandas as pd


class AccountBudgetReport(models.TransientModel):
    """Account Budget Report Wizard"""

    _name = 'account_budget_report'
    _description = __doc__

    filename = fields.Char('File Name', readonly=True)
    data = fields.Binary('File data', readonly=True, help='File(jpg, csv, xls, exe, any binary or text format)')

    def action_process_report_xlsx(self):
        row_list = []
        aa_ids = self.env['account.account'].sudo().search([])
        for aa in aa_ids:
            bp_ids = self.env['account.budget.post'].search([('account_ids', '=', aa.id)])
            prod_ids = self.env['product.template'].with_context(force_company=aa.company_id.id).search(
                [('property_account_expense_id', '=', aa.id)])
            data = {'Company': aa.company_id.name, 'Chart of accounts/Account code': aa.code,
                    'Chart of accounts/Name': aa.name, 'Chart of accounts/Type': aa.internal_type,
                    'Configuration / Budgetary position name': ';'.join([bp.name for bp in bp_ids]),
                    'Products': ';'.join([prod.name for prod in prod_ids])}
            row_list.append(data)
        df = pd.DataFrame(row_list)
        with io.BytesIO() as buf:
            writer = pd.ExcelWriter(buf, engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            writer.save()
            xlsx_data = base64.b64encode(buf.getvalue())

        name = 'account_budget_report-{}'.format(fields.Date.today())
        extension = 'xlsx'
        filename = "%s.%s" % (name, extension)
        self.write({'filename': filename, 'data': xlsx_data})
        report = self.env.ref('accounting_reports_allea.account_budget_wizard_form_wizard')
        new_action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account_budget_report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(report.id, 'form')],
            'target': 'new',
        }

        return new_action
