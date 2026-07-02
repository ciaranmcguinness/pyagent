from svc_types import Service
from agents import function_tool, FunctionTool


def install():
    def get_tools() -> list[FunctionTool]:
        @function_tool
        def create_job(description:str, time: int, repeat:bool, persist:bool):
            """Create a new cron job to execute in [time] seconds, which will run you with the prompt given in description. Repeat leads to it triggering every [time] seconds. Persist leads to it staying between restarts. Time on a job ticks while cron isn't running if the job is persisted."""
            pass
        @function_tool
        def list_jobs():
            pass
        @function_tool
        def delete_job(id:int):
            pass
        return []
    def get_services() -> list[Service]:
        def boot():
            return
        def shutdown():
            return
        return [Service(boot, 'on_start'), Service(shutdown, 'on_exit')]
    return (get_tools,get_services)