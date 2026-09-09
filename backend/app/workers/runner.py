"""Standalone scheduler process for scaled deployments.

Run the recurring background loops (journal reminders, celebrations) as their
own process so that ANY number of API workers can run with RUN_WORKERS=false
without duplicating notifications:

    python -m app.workers.runner

Intended entrypoint for the `sentinel-scheduler` docker/render service.
"""

import asyncio


async def run() -> None:
    from app.workers.celebrations_worker import celebrations_loop
    from app.workers.reminder_worker import reminder_loop

    await asyncio.gather(reminder_loop(), celebrations_loop())


if __name__ == "__main__":
    asyncio.run(run())
