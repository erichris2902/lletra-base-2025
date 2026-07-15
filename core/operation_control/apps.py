from django.apps import AppConfig


class OperationControlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.operation_control"
    verbose_name = "Control Maestro de Operaciones"

    def ready(self):
        import core.operation_control.signals