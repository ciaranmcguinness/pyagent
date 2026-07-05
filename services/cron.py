from agents import function_tool, FunctionTool
from dataclasses import dataclass
import os
import dill
import time
import asyncio

@dataclass
class CronJob():
    duration: int
    start_time: int
    repeat: bool
    prompt: str
    description: str

@dataclass
class CronData():
    jobs: list[CronJob]

@dataclass
class Cron():
    data: CronData
    bg: asyncio.Task
    new_data: asyncio.Future[None|CronJob]

    def get_tools(self) -> list[FunctionTool]:
        @function_tool
        def create_reminder(prompt:str, description:str, duration: int, repeat:bool) -> str:
            """Creates a scheduled reminder for you, invoking you with the prompt specified after the number of seconds specified elapses.
If repeat is true, the reminder will be rescheduled after each invocation.
If duration is zero, the reminder will run once on startup. This is only useful if repeat is true, as otherwise, the reminder will be deleted before the next boot.
Elapsed time continues while the scheduler is offline, If one or more invocations of a job is missed while offline, a single invocation is performed when the scheduler resumes.
Returns the id of the new job if successful or error details if not. IDs are not consistent, so do not depend on them if a reminder needs to be tracked accross boots or after a deletion."""
            if prompt.strip() == "":
                return "Error: Prompt cannot be empty!"
            if duration < 0:
                return "Error: duration cannot be less than 0."
            id = len(self.data.jobs)
            if self.new_data.done():
                while self.new_data.done():
                    try:
                        if self.new_data.result() == None:
                            return "Error: Cannot create a new job during shutdown."
                    except asyncio.InvalidStateError:
                        break

            self.new_data.set_result(CronJob(duration, 0, repeat, prompt, description))
            return f"Success! ID: {id}"

        @function_tool
        def list_reminders():
            r = []
            for i, j in enumerate(self.data.jobs):
                r.append(f"Reminder {i}: description:{j.description} repeat:{j.repeat} duration:{j.duration}")
            return "\n".join(r)

        @function_tool
        def get_reminder_prompt(id: int) -> str:
            """Get the prompt for a reminder."""
            if len(self.data.jobs) >= id:
                return "No such reminder."
            return self.data.jobs[id].prompt

        @function_tool
        def delete_reminder(id:int) -> str:
            """Delete a reminder, reminders with higher ids have their IDs decremented."""
            if id >= len(self.data.jobs):
                return f"Error: No reminder with id {id}."
            self.data.jobs.pop(id)
            return "Success!"
            
        return [create_reminder, list_reminders, get_reminder_prompt, delete_reminder]

    def get_start_fn(self):
        def remind(gate, job: CronJob):
            pass
            

        async def wait_reminder(gate, job: CronJob):
            elapsed = time.time() - job.start_time
            if job.duration > elapsed:
                await asyncio.sleep(job.duration - elapsed)
            remind(gate, job)
            return job

        async def bg(gate):
            for job in filter(lambda x: x.duration == 0, self.data.jobs):
                remind(gate, job)
            async with asyncio.TaskGroup() as tg:
                job_tasks: set[asyncio.Future[CronJob | None] | asyncio.Task[CronJob]] = set(map(lambda y: tg.create_task(wait_reminder(gate,y)), filter(lambda x: x.duration != 0, self.data.jobs)))
                cont = True
                while cont:
                    job_tasks.add(self.new_data)
                    done, pending = await asyncio.wait(job_tasks, return_when=asyncio.FIRST_COMPLETED)
                    job_tasks = pending
                    for item in map(lambda x: x.result(), done):
                        if item == None:
                            cont = False
                        else:
                            if not item.repeat:
                                if (item.start_time == 0):
                                    item.start_time = int(time.time())
                                    job_tasks.add(tg.create_task(wait_reminder(gate, item)))
                                else:
                                    self.data.jobs.pop(self.data.jobs.index(item))
                            else:
                                item.start_time = int(time.time())
                                job_tasks.add(tg.create_task(wait_reminder(gate, item)))

        def boot(a):
            if os.path.exists("./cron.dill"):
                with open("./cron.dill","rb") as f:
                    self.data = dill.load(f)
                    if not isinstance(self.data, CronData):
                        raise Exception("Invalid cron.dill!")
            loop = asyncio.new_event_loop()
            loop.set_task_factory(asyncio.eager_task_factory)
            self.bg = loop.create_task(bg(a))

        return boot

    def get_exit_fn(self):
        def shutdown(_):
            keep = []
            for i in self.data.jobs:
                if i.repeat:
                    keep.append(i)

            self.data.jobs = keep

            with open("./cron.dill", "wb") as f:
                dill.dump(self.data, f)

        return shutdown