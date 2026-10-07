# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cvat.apps.engine.models import (
    Data,
    Job,
    Label,
    LabeledShape,
    Segment,
    ShapeType,
    Task,
)
from cvat.apps.test.services import get_task_class_counts

User = get_user_model()


class AnalyticsServiceTestCase(TestCase):
    """
    Tests for the backend aggregation service get_task_class_counts().
    """

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.data = Data.objects.create(size=10, start_frame=0, stop_frame=9)
        self.task = Task.objects.create(name="Analytics Test Task", owner=self.user, data=self.data)
        self.segment = Segment.objects.create(task=self.task, start_frame=0, stop_frame=9)
        self.job = Job.objects.create(segment=self.segment)

        # Labels
        self.label_car = Label.objects.create(name="car", color="#ff0000", task=self.task)
        self.label_person = Label.objects.create(name="person", color="#00ff00", task=self.task)

    def test_get_task_class_counts_empty(self):
        """
        Task with no annotations should return 0 counts for all defined labels.
        """
        result = get_task_class_counts(self.task.id)

        self.assertEqual(result["task_id"], self.task.id)
        self.assertEqual(result["task_name"], "Analytics Test Task")
        self.assertEqual(result["total_frames"], 10)
        self.assertEqual(result["total_annotated_images"], 0)
        self.assertEqual(result["total_annotations"], 0)
        self.assertEqual(len(result["classes"]), 2)

        car_stats = next(c for c in result["classes"] if c["name"] == "car")
        self.assertEqual(car_stats["image_count"], 0)
        self.assertEqual(car_stats["annotation_count"], 0)
        self.assertEqual(car_stats["annotated_frames"], [])

    def test_get_task_class_counts_with_shapes(self):
        """
        Verify distinct frame counting: multiple shapes on the same frame count as 1 image.
        """
        # Frame 0: 2 cars
        LabeledShape.objects.create(
            job=self.job,
            label=self.label_car,
            frame=0,
            type=ShapeType.RECTANGLE,
            points=[10.0, 10.0, 50.0, 50.0],
        )
        LabeledShape.objects.create(
            job=self.job,
            label=self.label_car,
            frame=0,
            type=ShapeType.RECTANGLE,
            points=[60.0, 60.0, 90.0, 90.0],
        )
        # Frame 2: 1 car
        LabeledShape.objects.create(
            job=self.job,
            label=self.label_car,
            frame=2,
            type=ShapeType.RECTANGLE,
            points=[15.0, 15.0, 45.0, 45.0],
        )
        # Frame 2: 1 person
        LabeledShape.objects.create(
            job=self.job,
            label=self.label_person,
            frame=2,
            type=ShapeType.RECTANGLE,
            points=[100.0, 100.0, 150.0, 200.0],
        )

        result = get_task_class_counts(self.task.id)

        self.assertEqual(result["total_annotated_images"], 2)  # Frames 0 and 2
        self.assertEqual(result["total_annotations"], 4)      # 3 cars + 1 person

        car_stats = next(c for c in result["classes"] if c["name"] == "car")
        self.assertEqual(car_stats["image_count"], 2)         # Frames 0 and 2
        self.assertEqual(car_stats["annotation_count"], 3)    # 3 shapes
        self.assertEqual(car_stats["annotated_frames"], [0, 2])

        person_stats = next(c for c in result["classes"] if c["name"] == "person")
        self.assertEqual(person_stats["image_count"], 1)      # Frame 2 only
        self.assertEqual(person_stats["annotation_count"], 1)
        self.assertEqual(person_stats["annotated_frames"], [2])

    def test_nonexistent_task_raises_error(self):
        """
        Querying a non-existent task ID should raise Task.DoesNotExist.
        """
        with self.assertRaises(Task.DoesNotExist):
            get_task_class_counts(999999)


class AnalyticsAPITestCase(TestCase):
    """
    Tests for the REST API endpoint: GET /api/test/analytics/class-counts/
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="api_user", password="password123")
        self.data = Data.objects.create(size=5, start_frame=0, stop_frame=4)
        self.task = Task.objects.create(name="API Test Task", owner=self.user, data=self.data)
        self.segment = Segment.objects.create(task=self.task, start_frame=0, stop_frame=4)
        self.job = Job.objects.create(segment=self.segment)
        self.label = Label.objects.create(name="vehicle", color="#0000ff", task=self.task)

    def test_unauthenticated_request_forbidden(self):
        """
        Unauthenticated requests should be rejected with 401 Unauthorized.
        """
        response = self.client.get("/api/test/analytics/class-counts/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get_class_counts_success(self):
        """
        Authenticated request returns 200 with structured analytics data.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/test/analytics/class-counts/?task_id={self.task.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task.id)
        self.assertEqual(response.data["task_name"], "API Test Task")
        self.assertEqual(response.data["total_frames"], 5)
        self.assertIn("classes", response.data)
        self.assertEqual(len(response.data["classes"]), 1)
        self.assertEqual(response.data["classes"][0]["name"], "vehicle")

    def test_invalid_task_id_format(self):
        """
        Non-integer task_id query parameter returns 400 Bad Request.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/test/analytics/class-counts/?task_id=not_an_int")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_task_not_found(self):
        """
        Non-existent task ID returns 404 Not Found.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/test/analytics/class-counts/?task_id=999999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_default_task_id_fallback(self):
        """
        Omitting task_id parameter defaults to the first available task in the DB.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/test/analytics/class-counts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task.id)
