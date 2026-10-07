# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path
from .views import ClassCountAnalyticsView

urlpatterns = [
    path("test/analytics/class-counts/", ClassCountAnalyticsView.as_view(), name="class-counts-analytics"),
]
