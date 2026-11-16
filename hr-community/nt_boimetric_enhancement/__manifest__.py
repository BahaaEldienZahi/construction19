# -*- coding: utf-8 -*-
{
    'name': "National Boimetric Enhancement",

    'summary': """
    convert  boimetric log to employees attendaces Enhancement.
    """,

    'description': "",

    'author': "National Technology",
    'website': "https://nt-me.com/",
    'sequence': -100,
    'category': 'hr',
    'version': '0.1',
    "license": "AGPL-3",
    # any module necessary for this one to work correctly
    'depends': ['hr', 'hr_attendance', 'rm_hr_attendance_sheet', 'cds_bio_attendance'],
    'application': True,

    # always loaded
    'data': [
        'views/bio_enhancement_bt.xml',

    ],
}
