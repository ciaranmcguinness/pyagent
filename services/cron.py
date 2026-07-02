from svc_types import Service
from agents import function_tool, FunctionTool
from dataclasses import dataclass
import os
import dill
import time

@dataclass
class CronJob():
    duration: int
    start_time: int
    repeat: bool
    persist: bool
    prompt: str
    description: str

@dataclass
class CronData():
    jobs: list[CronJob]

@dataclass
class Box():
    inner: CronData

def install():
    b = Box(CronData([]))
    def get_tools() -> list[FunctionTool]:
        @function_tool
        def create_reminder(prompt:str, description:str, duration: int, repeat:bool, persist:bool) -> str:
            """Creates a scheduled reminder for you, invoking you with the prompt specified after the number of seconds specified elapses.
If repeat is true, it will be invoked every time seconds thereafter. If persist is true, the job survives restarts, and elapsed time continues while the scheduler is offline.
If one or more invocations of a persisted job is missed while offline, a single invocation is performed when the scheduler resumes.
Returns the id of the new job if successful or error details if not."""
            if prompt.strip() == "":
                return "Error: Prompt cannot be empty!"
            if duration < 60:
                return "Error: time cannot be less than 60 seconds."
            id = len(b.inner.jobs)
            b.inner.jobs.append(CronJob(duration,int(time.time()), repeat,persist,prompt, description))
            return f"Success! ID: {id}"

        @function_tool
        def list_reminders():
            r = []
            for i, j in enumerate(b.inner.jobs):
                r.append(f"Reminder {i}: description:{j.description} repeat:{j.repeat} persist:{j.persist} duration:{j.duration}")
            return "\n".join(r)

        @function_tool
        def get_reminder_prompt(id: int) -> str:
            """Get the prompt for a reminder."""
            if len(b.inner.jobs) >= id:
                return "No such reminder."
            return b.inner.jobs[id].prompt

        @function_tool
        def delete_reminder(id:int) -> str:
            """Delete a reminder, reminders with higher ids have their IDs decremented."""
            if id >= len(b.inner.jobs):
                return f"Error: No reminder with id {id}."
            b.inner.jobs.pop(id)
            return "Success!"
            
        return [create_reminder, list_reminders, get_reminder_prompt, delete_reminder]
    def get_services() -> list[Service]:
        def boot(a):
            if os.path.exists("./cron.dill"):
                with open("./cron.dill","rb") as f:
                    b.inner = dill.load(f)
                    if not isinstance(b.inner, CronData):
                        raise Exception("Invalid cron.dill!")

        def shutdown(_):
            to_rm = []
            for i, j in enumerate(b.inner.jobs):
                if not j.persist:
                    to_rm.append(i)
            for i in to_rm:
                b.inner.jobs.pop(i)

            with open("./cron.dill", "wb") as f:
                dill.dump(b.inner, f)
        return [Service(boot, 'on_start'), Service(shutdown, 'on_exit')]
    return (get_tools,get_services)