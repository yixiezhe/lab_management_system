from django.apps import AppConfig

class ProcurementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'procurement'

    # The ready() method that imported signals has been removed
    # as the old reimbursement functionality is now deprecated.