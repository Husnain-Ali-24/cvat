# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.apps import AppConfig


class TestConfig(AppConfig):
    name = "cvat.apps.test"
    verbose_name = "CVAT Analytics Test App"

    def ready(self) -> None:
        from . import signals  # pylint: disable=unused-import
