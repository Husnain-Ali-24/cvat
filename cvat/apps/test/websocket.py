# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, Set, Tuple
from urllib.parse import parse_qs

import redis
import redis.asyncio as aioredis
from asgiref.sync import sync_to_async

from .services import get_task_class_counts

logger = logging.getLogger(__name__)

REDIS_CHANNEL = "cvat_analytics_broadcast"

# Registry of active local subscribers in this Uvicorn process:
# (loop, queue, task_id)
_subscribers: Set[Tuple[asyncio.AbstractEventLoop, asyncio.Queue, int | None]] = set()
_listener_started = False


def _get_redis_sync():
    host = os.getenv("CVAT_REDIS_INMEM_HOST", "cvat_redis_inmem")
    port = int(os.getenv("CVAT_REDIS_INMEM_PORT", 6379))
    return redis.Redis(host=host, port=port)


def register_subscriber(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, task_id: int | None) -> None:
    _subscribers.add((loop, queue, task_id))


def unregister_subscriber(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, task_id: int | None) -> None:
    _subscribers.discard((loop, queue, task_id))


def broadcast_task_update_sync(task_id: int) -> None:
    """
    Called synchronously from Django signals (post_save / post_delete).
    Publishes event to Redis so all Uvicorn worker processes broadcast to their clients.
    """
    try:
        r = _get_redis_sync()
        r.publish(REDIS_CHANNEL, json.dumps({"task_id": task_id}))
    except Exception as exc:
        logger.error(f"Failed to publish update to Redis for task {task_id}: {exc}")


async def _start_redis_listener_if_needed():
    global _listener_started
    if _listener_started:
        return
    _listener_started = True

    async def _listener():
        host = os.getenv("CVAT_REDIS_INMEM_HOST", "cvat_redis_inmem")
        port = int(os.getenv("CVAT_REDIS_INMEM_PORT", 6379))
        try:
            r = aioredis.from_url(f"redis://{host}:{port}/0")
            pubsub = r.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL)
            logger.info("Subscribed to Redis analytics broadcast channel")

            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        payload = json.loads(message["data"])
                        task_id = payload.get("task_id")
                        if task_id is not None:
                            # Recalculate counts in background thread
                            fresh_data = await sync_to_async(get_task_class_counts)(task_id)
                            msg_payload = json.dumps({
                                "event": "class_counts_updated",
                                "data": fresh_data,
                            })
                            # Dispatch to all relevant local queues
                            for loop, queue, sub_task_id in list(_subscribers):
                                if sub_task_id is None or sub_task_id == task_id:
                                    queue.put_nowait(msg_payload)
                except Exception as loop_err:
                    logger.warning(f"Error in Redis listener iteration: {loop_err}")
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Redis listener task terminated: {e}")

    asyncio.create_task(_listener())


async def websocket_application(scope: Dict[str, Any], receive: Any, send: Any) -> None:
    """
    Pure ASGI 3.0 WebSocket Application for Real-Time Analytics.
    URL Path: /api/test/analytics/ws/ or /api/test/analytics/ws/<task_id>/
    """
    await _start_redis_listener_if_needed()

    path = scope.get("path", "")
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string)

    task_id: int | None = None
    match = re.search(r"/api/test/analytics/ws/(?:(\d+)/)?", path)
    if match and match.group(1):
        try:
            task_id = int(match.group(1))
        except ValueError:
            pass

    if task_id is None and "task_id" in query_params:
        try:
            task_id = int(query_params["task_id"][0])
        except (ValueError, IndexError):
            pass

    # Accept incoming WebSocket connection
    await send({"type": "websocket.accept"})

    loop = asyncio.get_running_loop()
    send_queue: asyncio.Queue = asyncio.Queue()
    register_subscriber(loop, send_queue, task_id)

    # Immediately push initial class counts
    if task_id is not None:
        try:
            initial_data = await sync_to_async(get_task_class_counts)(task_id)
            send_queue.put_nowait(json.dumps({
                "event": "initial_data",
                "data": initial_data,
            }))
        except Exception as exc:
            send_queue.put_nowait(json.dumps({
                "event": "error",
                "detail": f"Failed to load task {task_id}: {str(exc)}",
            }))

    # Dedicated message pump task
    async def _sender():
        try:
            while True:
                msg_text = await send_queue.get()
                await send({
                    "type": "websocket.send",
                    "text": msg_text,
                })
                send_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Error in websocket sender: {e}")

    sender_task = asyncio.create_task(_sender())

    try:
        while True:
            message = await receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            elif msg_type == "websocket.receive":
                text = message.get("text", "")
                if text:
                    try:
                        cmd = json.loads(text)
                        action = cmd.get("action")

                        if action == "ping":
                            send_queue.put_nowait(json.dumps({"event": "pong"}))

                        elif action == "subscribe":
                            new_task_id = cmd.get("task_id")
                            if new_task_id is not None:
                                unregister_subscriber(loop, send_queue, task_id)
                                task_id = int(new_task_id)
                                register_subscriber(loop, send_queue, task_id)
                                fresh_data = await sync_to_async(get_task_class_counts)(task_id)
                                send_queue.put_nowait(json.dumps({
                                    "event": "subscribed",
                                    "data": fresh_data,
                                }))
                    except Exception as exc:
                        send_queue.put_nowait(json.dumps({
                            "event": "error",
                            "detail": str(exc),
                        }))

    finally:
        unregister_subscriber(loop, send_queue, task_id)
        sender_task.cancel()
