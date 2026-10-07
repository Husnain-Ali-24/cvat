# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

import logging
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cvat.apps.engine.models import LabeledImage, LabeledShape, TrackedShape, Job
from .websocket import broadcast_task_update_sync

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1. Direct Django Model Signals (for direct ORM operations & unit tests)
# ----------------------------------------------------------------------
@receiver([post_save, post_delete], sender=LabeledShape)
def on_labeled_shape_changed(sender, instance: LabeledShape, **kwargs):
    try:
        task_id = instance.job.segment.task_id
        broadcast_task_update_sync(task_id)
    except Exception as exc:
        logger.warning(f"Error in on_labeled_shape_changed signal: {exc}")


@receiver([post_save, post_delete], sender=TrackedShape)
def on_tracked_shape_changed(sender, instance: TrackedShape, **kwargs):
    try:
        task_id = instance.track.job.segment.task_id
        broadcast_task_update_sync(task_id)
    except Exception as exc:
        logger.warning(f"Error in on_tracked_shape_changed signal: {exc}")


@receiver([post_save, post_delete], sender=LabeledImage)
def on_labeled_image_changed(sender, instance: LabeledImage, **kwargs):
    try:
        task_id = instance.job.segment.task_id
        broadcast_task_update_sync(task_id)
    except Exception as exc:
        logger.warning(f"Error in on_labeled_image_changed signal: {exc}")


# ----------------------------------------------------------------------
# 2. CVAT Dataset Manager Plugin Hooks (for UI workspace annotation saves)
# When users save annotations in the CVAT workspace, CVAT uses bulk_create
# inside patch_job_data / put_job_data, which bypasses post_save signals.
# The plugin system ensures we broadcast updates on every workspace save.
# ----------------------------------------------------------------------
def _on_job_annotations_saved(pk, *args, **kwargs):
    try:
        task_id = Job.objects.filter(pk=pk).values_list("segment__task_id", flat=True).first()
        if task_id:
            logger.info(f"Broadcasting real-time analytics update for task {task_id} from job {pk}")
            broadcast_task_update_sync(task_id)
    except Exception as exc:
        logger.warning(f"Error in _on_job_annotations_saved plugin: {exc}")


def _on_task_annotations_saved(pk, *args, **kwargs):
    try:
        logger.info(f"Broadcasting real-time analytics update for task {pk}")
        broadcast_task_update_sync(pk)
    except Exception as exc:
        logger.warning(f"Error in _on_task_annotations_saved plugin: {exc}")


try:
    from cvat.apps.engine.plugins import add_plugin
    add_plugin("patch_job_data", _on_job_annotations_saved, "after")
    add_plugin("put_job_data", _on_job_annotations_saved, "after")
    add_plugin("delete_job_data", _on_job_annotations_saved, "after")
    add_plugin("patch_task_data", _on_task_annotations_saved, "after")
    add_plugin("put_task_data", _on_task_annotations_saved, "after")
    add_plugin("delete_task_data", _on_task_annotations_saved, "after")
    logger.info("Successfully registered CVAT annotation save plugins for real-time analytics.")
except Exception as plugin_err:
    logger.warning(f"Could not attach CVAT dataset_manager plugins: {plugin_err}")
