# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set
from django.utils import timezone
from cvat.apps.engine.models import (
    Task,
    Label,
    LabeledShape,
    TrackedShape,
    LabeledImage,
)


def get_task_class_counts(task_id: int) -> Dict[str, Any]:
    """
    Extract annotation data and aggregate class-wise image counts for a given task.
    
    A class-wise image count represents the number of unique images (frames)
    that contain at least one annotation of a given label.

    Optimization Note:
    All aggregations are performed in O(1) database queries (constant 5 queries total)
    rather than looping over labels (which would cause an N+1 query problem).
    """
    # 1. Fetch task and its related Data in a single query
    task = Task.objects.select_related("data").get(pk=task_id)
    labels = list(task.get_labels())
    total_frames = task.data.size if task.data else 0

    # 2. Batch-fetch ALL LabeledShapes for this task in ONE query (O(1) instead of 2*N queries)
    shape_frames_by_label: Dict[int, Set[int]] = defaultdict(set)
    shape_counts_by_label: Dict[int, int] = defaultdict(int)

    shape_rows = LabeledShape.objects.filter(
        job__segment__task_id=task.id,
    ).values_list("label_id", "frame")

    for lbl_id, frame in shape_rows:
        shape_frames_by_label[lbl_id].add(frame)
        shape_counts_by_label[lbl_id] += 1

    # 3. Batch-fetch ALL TrackedShapes for this task in ONE query (O(1) instead of 2*N queries)
    track_frames_by_label: Dict[int, Set[int]] = defaultdict(set)
    track_counts_by_label: Dict[int, int] = defaultdict(int)

    track_rows = TrackedShape.objects.filter(
        track__job__segment__task_id=task.id,
        outside=False,
    ).values_list("track__label_id", "frame")

    for lbl_id, frame in track_rows:
        track_frames_by_label[lbl_id].add(frame)
        track_counts_by_label[lbl_id] += 1

    # 4. Batch-fetch ALL LabeledImages for this task in ONE query (O(1) instead of 2*N queries)
    image_frames_by_label: Dict[int, Set[int]] = defaultdict(set)
    image_counts_by_label: Dict[int, int] = defaultdict(int)

    image_rows = LabeledImage.objects.filter(
        job__segment__task_id=task.id,
    ).values_list("label_id", "frame")

    for lbl_id, frame in image_rows:
        image_frames_by_label[lbl_id].add(frame)
        image_counts_by_label[lbl_id] += 1

    # 5. In-memory aggregation per label (0 additional database queries)
    classes_data: List[Dict[str, Any]] = []
    total_annotations_in_task = 0
    all_annotated_frames: Set[int] = set()

    for label in labels:
        s_frames = shape_frames_by_label.get(label.id, set())
        t_frames = track_frames_by_label.get(label.id, set())
        i_frames = image_frames_by_label.get(label.id, set())

        # Aggregate unique frames containing this label
        unique_frames = s_frames | t_frames | i_frames
        annotation_count = (
            shape_counts_by_label.get(label.id, 0)
            + track_counts_by_label.get(label.id, 0)
            + image_counts_by_label.get(label.id, 0)
        )

        all_annotated_frames.update(unique_frames)
        total_annotations_in_task += annotation_count

        classes_data.append({
            "id": label.id,
            "name": label.name,
            "color": label.color,
            "image_count": len(unique_frames),
            "annotation_count": annotation_count,
            "annotated_frames": sorted(list(unique_frames)),
        })

    return {
        "task_id": task.id,
        "task_name": task.name,
        "total_frames": total_frames,
        "total_annotated_images": len(all_annotated_frames),
        "total_annotations": total_annotations_in_task,
        "classes": classes_data,
        "updated_at": timezone.now().isoformat(),
    }
