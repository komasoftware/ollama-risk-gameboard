import logging
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
from functools import wraps

def wrap_mcp_toolset_with_logging(mcp_toolset):
    logger = logging.getLogger("LoggingMCPToolset")
    for attr in dir(mcp_toolset):
        if attr.startswith("_"):
            continue
        func = getattr(mcp_toolset, attr)
        if callable(func):
            @wraps(func)
            async def wrapper(*args, __func=func, __name=attr, **kwargs):
                logger.info(f"[MCPToolset] Tool called: {__name} args={args} kwargs={kwargs}")
                return await __func(*args, **kwargs)
            setattr(mcp_toolset, attr, wrapper)
    return mcp_toolset 