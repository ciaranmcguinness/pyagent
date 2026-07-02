from agents import function_tool
import pathlib

@function_tool
def read_file(path:str) -> str:
    """Read the file at the path"""
    try:
        pth = pathlib.Path(path)
        return pth.read_text()
    except Exception as e:
        return "Error: "+  str(e).split("] ")[1]
    
@function_tool
def pwd() -> str:
    """Read the file at the path"""
    try:
        return str(pathlib.Path.cwd())
    except Exception as e:
        return "Error: "+  str(e).split("] ")[1]
    
@function_tool
def ls(path:str) -> str:
    """Read the file at the path"""
    try:
        pth = pathlib.Path(path)
        return ", ".join(list(map(lambda x: x.name, pth.iterdir())))
    except Exception as e:
        return "Error: "+  str(e).split("] ")[1]