# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cvat.apps.engine.models import Task
from cvat.apps.engine.permissions import TaskPermission

from .serializers import TaskClassCountsSerializer
from .services import get_task_class_counts


@extend_schema(
    tags=["analytics"],
    summary="Get class-wise image and annotation counts for a task",
    description=(
        "Extracts annotation data for a specified task and calculates the number "
        "of unique images (frames) containing each class, as well as total annotation counts."
    ),
    parameters=[
        OpenApiParameter(
            name="task_id",
            description="ID of the task to calculate class-wise analytics for (defaults to first available task)",
            required=False,
            type=int,
        ),
    ],
    responses={
        200: TaskClassCountsSerializer,
        400: {"description": "Invalid task ID"},
        401: {"description": "Authentication credentials required"},
        403: {"description": "Permission denied for this task"},
        404: {"description": "Task not found"},
    },
)
class ClassCountAnalyticsView(APIView):
    """
    API endpoint for class-wise image and annotation counts.
    Usage: GET /api/test/analytics/class-counts/?task_id=<id>
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TaskClassCountsSerializer

    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get("task_id")

        if not task_id:
            first_task = Task.objects.order_by("id").first()
            if not first_task:
                return Response(
                    {"detail": "No tasks found in the database."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            task_id = first_task.id

        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": f"Invalid task_id: '{task_id}'. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = Task.objects.filter(pk=task_id).first()
        if not task:
            return Response(
                {"detail": f"Task with ID {task_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Enforce task object-level permissions (Requirement 5)
        try:
            perm = TaskPermission.create_scope_view(request, task)
            if not perm.allow:
                return Response(
                    {"detail": f"You do not have permission to access task {task_id}."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Exception:
            # Fallback permission check: allow superusers, task owner, or assignee
            if not (
                request.user.is_superuser
                or getattr(task, "owner_id", None) == request.user.id
                or getattr(task, "assignee_id", None) == request.user.id
            ):
                return Response(
                    {"detail": f"You do not have permission to access task {task_id}."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            analytics_data = get_task_class_counts(task_id)
            serializer = self.serializer_class(analytics_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"detail": f"Failed to compute class counts: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
