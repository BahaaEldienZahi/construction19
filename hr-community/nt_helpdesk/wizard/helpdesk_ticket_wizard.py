# -*- coding: utf-8 -*-


import io
import base64
import xlsxwriter
from datetime import datetime
import pytz

from odoo import fields, models, _

from odoo.exceptions import ValidationError


class HelpdeskTicketWizard(models.TransientModel):
    _name = 'helpdesk.ticket.wizard'
    _description = 'Helpdesk Ticket Wizard Report'

    start_date = fields.Date(string="Start Date",
                             required=True,
                             help="Starting date")
    end_date = fields.Date(string="End Date",
                           required=True,
                           help="Ending date")
    team_id = fields.Many2one('helpdesk.ticket.team', string='Helpdesk Team', required=True)
    only_previous = fields.Boolean(string="Only Previous Tickets", default=False)

    def get_previous_tickets(self):
        """Get previous tickets for the selected team"""
        stage_field_id = self.env['ir.model.fields'].sudo().search([
            ('name', '=', 'team_id'),
            ('model_id.model', '=', 'helpdesk.ticket')
        ], limit=1)
        mtv_tickets = self.env['mail.tracking.value'].sudo().search([
            ('field_id', '=', stage_field_id.id),
            ('mail_message_id.date', '>=', self.start_date),
            ('mail_message_id.date', '<=', self.end_date),
            ('old_value_char', '=', self.team_id.name),
        ])
        previous_tickets = self.env['helpdesk.ticket'].sudo().browse([int(mtv_ticket.mail_message_id.res_id) for mtv_ticket in
                                                               mtv_tickets])
        return previous_tickets

    def action_generate_xlsx_report(self):

        if self.start_date > self.end_date:
            raise ValidationError(_("The End Date must be greater than the Start Date"))

        data = []
        if self.start_date and self.end_date:
            if self.only_previous:
                all_tickets = self.get_previous_tickets()
            else:
                all_tickets = self.env['helpdesk.ticket'].sudo().search([
                    ('team_id', '=', self.team_id.id),
                    ('create_date', '>=', self.start_date),
                    ('create_date', '<=', self.end_date)
                ])
            if all_tickets:
                for ticket in all_tickets:
                    # if not ticket.first_user_id:
                    #     ticket.compute_first_user_id()
                    # ticket.compute_to_check_date()
                    # ticket.compute_close_date()
                    user_tz = self.env.user.tz or str(pytz.UTC)
                    local = pytz.timezone(user_tz)
                    result = {
                        'ticket_number': ticket.number or '-',
                        'created_date': (ticket.create_date.replace(tzinfo=pytz.utc).astimezone(local).replace(tzinfo=None).strftime(
                                '%Y-%m-%d %H:%M:%S')
                            if ticket.create_date else '-'
                        ),
                        'customer': ticket.partner_id.name or '-',
                        'created_by': ticket.create_uid.name if ticket.create_uid else '-',
                        'first_assigned_to': ticket.first_user_id.name if ticket.first_user_id else '-',
                        'first_assigned_date': (
                            '-' if not ticket.assigned_date
                            else ticket.assigned_date.replace(tzinfo=pytz.utc).astimezone(local).replace(tzinfo=None)
                        ),
                        'current_assigned': ticket.user_id.name if ticket.user_id else '-',
                        'to_check_date': (
                            '-' if not ticket.to_check_date
                            else ticket.to_check_date.replace(tzinfo=pytz.utc).astimezone(local).replace(tzinfo=None)
                        ),
                        'close_date': (
                            '-' if not ticket.close_date
                            else ticket.close_date.replace(tzinfo=pytz.utc).astimezone(local).replace(tzinfo=None)
                        ),
                        'status': ticket.stage_id.name or '-',
                        'status_progress': (
                            '-' if not ticket.to_check_date
                            else (ticket.to_check_date - ticket.create_date)
                        ),
                        'first_helpdesk_team': ticket.last_team_id.name if ticket.last_team_id else '-',
                        'last_helpdesk_team': ticket.team_id.name or '-',
                        'area': ticket.helpdesk_area_id.name or '-',
                        'subarea': ticket.sub_area_id.name or '-',
                        'type': ticket.ticket_type_id.name or '-',
                        'tags': ', '.join(tag.name for tag in ticket.tag_ids) if ticket.tag_ids else '-',
                    }
                    data.append(result)

                date_range = f"From {self.start_date} To {self.end_date}"
                # Call the function to generate the Excel report
                file_content = self._generate_xlsx_report(data, date_range)

                # Prepare the file attachment
                filename = f'{self.team_id.name}_{date_range}_report.xlsx'
                attachment = {
                    'type': 'binary',
                    'name': filename,
                    'datas': base64.b64encode(file_content),
                    'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
                attachment_id = self.env['ir.attachment'].sudo().create(attachment)
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/{}?download=true'.format(attachment_id.id),
                    'target': 'self'
                }

    def _generate_xlsx_report(self, data, date_range):
        """Generate Excel report based on the data"""
        # Create an in-memory output stream
        output = io.BytesIO()

        # Create an Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Helpdesk Ticket Report')

        # Define formats
        bold2 = workbook.add_format(
            {'bold': True, 'locked': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 15, 'bottom': 1,
             'top': 1, 'right': 1, 'left': 1,
             'bg_color': '#7d7d7d', 'font_color': 'white'})
        bold1 = workbook.add_format(
            {'bold': True, 'locked': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 12, 'bottom': 1,
             'top': 1, 'right': 1, 'left': 1,
             'bg_color': '#AAAAAA', 'font_color': 'white'})
        bold = workbook.add_format(
            {'bold': True, 'locked': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'bottom': 1,
             'top': 1, 'right': 1, 'left': 1})

        # Write headers
        row = 1
        # today_datetime = data.get('today', datetime.now())  # Ensure 'today' is a datetime object
        date_format = workbook.add_format(
            {'num_format': 'yyyy-mm-dd hh:mm:ss',
             'bold': True, 'locked': True, 'align': 'center', 'valign': 'vcenter',
             'font_size': 10, 'bottom': 1,
             'top': 1, 'right': 1, 'left': 1})
        worksheet.merge_range(f"A{row}:Q{row}", f'Helpdesk Ticket Xlsx {date_range}', bold2)
        for col in range(16):
            worksheet.set_column(col, col, 30)
        worksheet.set_column(0, 15, 30)
        worksheet.set_row(0, 30)

        # Write report details
        worksheet.write(2, 0, 'Ticket Number', bold1)
        worksheet.write(2, 1, 'Created Date', bold1)
        worksheet.write(2, 2, 'Customer', bold1)
        worksheet.write(2, 3, 'Created By', bold1)
        worksheet.write(2, 4, 'First Assigned To (Support)', bold1)
        worksheet.write(2, 5, 'First Assigned Date (Support)', bold1)
        worksheet.write(2, 6, 'Current Assigned', bold1)
        worksheet.write(2, 7, 'To Check Date', bold1)
        worksheet.write(2, 8, 'Close Date', bold1)
        worksheet.write(2, 9, 'Status', bold1)
        worksheet.write(2, 10, 'Status Progress (TAT)', bold1)
        worksheet.write(2, 11, 'First Helpdesk Team', bold1)
        worksheet.write(2, 12, 'Last Help Desk Team', bold1)
        worksheet.write(2, 13, 'Area', bold1)
        worksheet.write(2, 14, 'SubArea', bold1)
        worksheet.write(2, 15, 'Type', bold1)
        worksheet.write(2, 15, 'Tags', bold1)

        if data:
            count_row = 3
            for ticket in data:
                worksheet.write(count_row, 0, ticket['ticket_number'], bold)
                worksheet.write(count_row, 1, ticket['created_date'], date_format)
                worksheet.write(count_row, 2, ticket['customer'], bold)
                worksheet.write(count_row, 3, ticket['created_by'], bold)
                worksheet.write(count_row, 4, ticket['first_assigned_to'], bold)
                worksheet.write(count_row, 5, ticket['first_assigned_date'], date_format)
                worksheet.write(count_row, 6, ticket['current_assigned'], bold)
                worksheet.write(count_row, 7, ticket['to_check_date'], date_format)
                worksheet.write(count_row, 8, ticket['close_date'], date_format)
                worksheet.write(count_row, 9, ticket['status'], bold)
                worksheet.write(count_row, 10, ticket['status_progress'], bold)
                worksheet.write(count_row, 11, ticket['first_helpdesk_team'], bold)
                worksheet.write(count_row, 12, ticket['last_helpdesk_team'], bold)
                worksheet.write(count_row, 13, ticket['area'], bold)
                worksheet.write(count_row, 14, ticket['subarea'], bold)
                worksheet.write(count_row, 15, ticket['type'], bold)
                worksheet.write(count_row, 15, ticket['tags'], bold)

                count_row += 1

        workbook.close()
        output.seek(0)
        return output.getvalue()
