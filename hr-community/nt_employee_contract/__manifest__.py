{
    'name': "Employee Contract Creation",
    'summary': """
    (1) create a new employee contract,
    (2) hide tabs from employee,
    """,
    'description': "",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'sequence': -100,
    'category': 'hr',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_contract', 'national_probation_period', 'mail', 'hr_payroll_community', 'national_employee',
                'rm_hr_attendance_sheet'],
    'application': 'True',
    'data': [
        # 'security/ir.model.access.csv',
        'data/archiving_contract_and_employee.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_contract.xml',
    ],
}
