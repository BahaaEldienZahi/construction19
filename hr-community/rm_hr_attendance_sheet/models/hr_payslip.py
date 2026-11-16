""" Initialize Hr Payslip """
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import format_date


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from',
                  'date_to')
    def _onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        self.company_id = employee.company_id
        if not self.contract_id or self.employee_id != self.contract_id.employee_id:  # Add a default contract if not already defined
            contracts = employee._get_contracts(date_from, date_to)

            if not contracts or not contracts[
                0].structure_type_id:
                self.contract_id = False
                self.struct_id = False
                return
            self.contract_id = contracts[0]
            self.struct_id = contracts[0].structure_type_id.id

        payslip_name = self.struct_id.name or _('Salary Slip')
        self.name = '%s - %s - %s' % (payslip_name, self.employee_id.name or '',
                                      format_date(self.env, self.date_to,
                                                  date_format="MMMM y"))

        # if date_to > date_utils.end_of(fields.Date.today(), 'month'):
        #     raise UserError(_(
        #         "This payslip can be erroneous! Work entries may not be generated for the period from %(start)s to %(end)s.",
        #         start=date_utils.add(
        #             date_utils.end_of(fields.Date.today(), 'month'), days=1),
        #         end=date_to,
        #     ))
        # else:
        #     pass
            # self.warning_message = False

        # self.worked_days_line_ids = self._get_new_worked_days_lines()
