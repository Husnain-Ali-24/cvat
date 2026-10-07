# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from rest_framework import serializers


class ClassCountItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Label ID")
    name = serializers.CharField(help_text="Label class name")
    color = serializers.CharField(help_text="Label hex color")
    image_count = serializers.IntegerField(help_text="Unique images containing this class")
    annotation_count = serializers.IntegerField(help_text="Total annotations drawn for this class")
    annotated_frames = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of frame indices containing this class",
    )


class TaskClassCountsSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(help_text="Task ID")
    task_name = serializers.CharField(help_text="Task name")
    total_frames = serializers.IntegerField(help_text="Total frames in the task")
    total_annotated_images = serializers.IntegerField(help_text="Number of images with at least one annotation")
    total_annotations = serializers.IntegerField(help_text="Grand total of all annotations across all classes")
    classes = ClassCountItemSerializer(many=True, help_text="Class-wise analytics list")
    updated_at = serializers.DateTimeField(help_text="Timestamp of computation")
