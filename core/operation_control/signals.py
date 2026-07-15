from django.db.models.signals import post_save
from django.dispatch import receiver

from core.operations_panel.models.operation import Operation
from core.operation_control.models import OperationMasterControl


@receiver(post_save, sender=Operation)
def create_operation_master_control(sender, instance: Operation, created: bool, **kwargs):
    """Create a master control row automatically when a new Operation is created.

    Does not overwrite existing administrative fields. Only ensures existence.
    """
    if not created:
        return

    OperationMasterControl.objects.get_or_create(
        operation=instance,
        defaults={
            "created_by": getattr(instance, "created_by", None),
        },
    )
