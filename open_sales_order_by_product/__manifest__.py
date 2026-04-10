{
    'name': 'Open Sales Order by Product',
    'version': '18.0.8.1',
    'category': 'Sales/Reporting',
    'summary': 'Open sales order by product (pending lines)',
    'author': 'ChatGPT Helper',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'stock'],
    'data': ['security/ir.model.access.csv', 'views/open_sales_report_views.xml'],
    'installable': True,
    'application': False,
}
