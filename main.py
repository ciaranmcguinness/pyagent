from dataclasses import dataclass
import inspect
import asyncio
from agents import Agent, Runner, Tool, function_tool, ModelSettings
from typing import IO, Any, Optional
from types import BuiltinFunctionType
import config
import agents
import dill
import importlib
import os
import pexpect

if config.openai_tracing != None:
    agents.set_tracing_export_api_key(config.openai_tracing)
else:
    agents.set_tracing_disabled(True)

@dataclass
class Value():
    name: str
    index_in_shelf: int

@dataclass 
class AgentState():
    current: Any
    shelf: dict[int, Any]
    agent: Agent

@dataclass
class HelpfulObjects():
    import_lib = importlib

class Command():
    def __init__(self, running:pexpect.spawn):
        self._r = running

    def stopped(self):
        return self._r.isalive() == False

    def read(self, max_size:int = -1):
        fails = 0
        buf = b""
        try:
            while True:
                buf += self._r.read_nonblocking(1,0)
                if max_size != -1:
                    if len(buf) >= max_size:
                        try:
                            return buf.decode()
                        except:
                            if fails < 10:
                                fails += 1
                                continue
                            else:
                                return buf
        except (pexpect.TIMEOUT, pexpect.EOF):
            return buf.decode()
    
    def write(self, val:str):
        self._r.write(val)
        self._r.stdin.flush()
    
    def wait(self):
        self._r.wait()

class Main():
    """Main class of the agent."""
    def __init__(self, state: AgentState):
        self.state = state
        self.objs = HelpfulObjects()

    async def run(self, inp):
        #await self.step()
        m = config.provider.get_model(config.model)
        a = state.agent
        a.model = m
        a.model_settings = config.settings
        a.tools = self.get_tools()
        self.state.shelf[0] = self
        return (await Runner.run(a,inp,max_turns=None)).to_input_list()

    def get_tools(self) -> list[Tool]:
        @function_tool
        def select(n: int) -> str:
            """Select a member of the currently selected object, and set it as the current object."""
            items = list(filter(lambda x: x[0][0] != "_", inspect.getmembers(self.state.current)))
            if len(items) > n:
                self.state.current = items[n][1]
                return "Success!"
            return "Invalid item."
        
        @function_tool
        def shelve(slot: int) -> str:
            """Place the current object onto the shelf, if the slot specified already contains a value, swap the current object and the object in the slot."""
            rep = self.state.shelf.get(slot)
            self.state.shelf[slot] = self.state.current
            if rep != None:
                self.state.current = rep
            return "Success!"
        
        @function_tool()
        def eval_tool(inp:str, values: list[Value]) -> str:
            """Eval the given string and set the current object to the result. The values dict has it's keys replaced with their underlying values on the shelf, then is passed to eval() as the value for globals."""
            env = {}
            for v in values:
                if v.index_in_shelf in self.state.shelf:
                    env[v.name] = self.state.shelf[v.index_in_shelf]
                else:
                    return f"Shelf has no entry of id {v.index_in_shelf}."
            try:
                self.state.current = eval(inp, globals=env)
                return "Success!"
            except Exception as e:
                return "Eval failed: " + str(e)
            
        @function_tool()
        def inspect_current() -> str:
            r = ["Currently selected:"]
            if callable(self.state.current):
                r.append((type(self.state.current).__name__ + " " + str(inspect.signature(self.state.current))))
            else:
                r.append((type(self.state.current).__name__ + " " + str(self.state.current)))
            members = inspect.getmembers(self.state.current)
            d = self.state.current.__doc__
            if d != None:
                r.append("Docstring:")
                r.append(d)
            r.append(f"Members and methods:")
            for n, m in enumerate(filter(lambda x: x[0][0] != "_", members)):
                mname = m[0]
                mval = m[1]
                if callable(mval):
                        if isinstance(mval, BuiltinFunctionType):
                            r.append(f"{n}: " + "builtin function " + mname)
                        else:
                            r.append(f"{n}: " + type(mval).__name__+ " " + mname + " " + str(inspect.signature(mval)))
                else:
                        r.append(f"{n}: " + "Member: (type "+type(mval).__name__+ ") " + mname + " " + str(mval))
            return "\n".join(r)

        @function_tool()
        def inspect_shelf() -> str:
            r = []
            if len(self.state.shelf) != 0:
                r.append("Contents of shelf:")
                for n, v in self.state.shelf.items():
                    if callable(v):
                        r.append(f"{n}: " + type(v).__name__+ " " + v.__name__+ " " + str(inspect.signature(v)))
                    else:
                        r.append(f"{n}: " + type(v).__name__ + ' (value: ' + str(v)+')')
            else:
                r.append("Shelf is empty!")
            return "\n".join(r)
        
        @function_tool
        def spawn_command(command:str, args: list[str]):
            """Start command and set currently held to command object."""
            try:
                self.state.current = Command(pexpect.spawn(command, args))
                return "Successfully started!"
            except Exception as e:
                return f"Error: {str(e)}"

        return [inspect_current, inspect_shelf, select, shelve, eval_tool, spawn_command] + config.tools

if __name__ == "__main__":
    state = AgentState(None,{},config.default_agent)
    if os.path.exists("./pyagent.dill"):
        with open("./pyagent.dill","rb") as f:
            state = dill.load(f)
            if not isinstance(state, AgentState):
                raise Exception("Invalid pyagent.dill!")
    m = Main(state)
    try:
        inp = []
        while True:
            inp.append({"role":"user","content":input(">")}) # type: ignore
            inp = asyncio.run(m.run(inp))
            print(inp[-1]["content"][0]["text"]) # type: ignore
            
    except KeyboardInterrupt:
        state.agent.tools = []
        state.agent.model = None
        state.agent.model_settings = ModelSettings()
        if dill.pickles(state.current) == False:
            state.current = None
        for k in state.shelf.keys():
            if dill.pickles(state.shelf[k]) == False:
                state.shelf[k] = None
        with open("./pyagent.dill", "wb") as f:
            dill.dump(state, f)