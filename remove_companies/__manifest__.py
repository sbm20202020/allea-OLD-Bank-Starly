{
    'name': "Remove companies",
    'summary': "Remove all records belongs to deleted companies",
    'version': "13.0.0.0.1",
    'author': 'Solopov.Nikita',
    'license': "AGPL-3",
    'application': False,
    'installable': True,
    'post_init_hook': 'init_remove_companies',
}
