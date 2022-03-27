from odoo import models


class BudgetSchedulerCompute(models.TransientModel):
    _name = 'budget.scheduler.compute'
    _description = 'Run Budget Scheduler Manually'

    def calculation(self):
        cbl_ids = self.env['crossovered.budget.lines'].search([])
        if cbl_ids:
            cbl_ids._compute_practical_amount()
        return {'type': 'ir.actions.act_window_close'}
