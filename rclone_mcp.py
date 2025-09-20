import asyncio
import logging
from typing import TypedDict

from mcp.server.fastmcp import FastMCP

from src.utils import get_logger


class Remotes(TypedDict):
    remotes: list[str]


logger = get_logger("mcp_logs")

rclone_mcp = FastMCP("rclone")


@rclone_mcp.tool()
async def listremotes() -> Remotes:
    process = await asyncio.create_subprocess_exec(
        "rclone", "listremotes", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    out, err = await process.communicate()

    if err:
        logger.error(err.decode().strip())

    if process.returncode != 0:
        logger.error(f"rclone listremotes failed with code {process.returncode}")
        raise RuntimeError(f"rclone listremotes failed with code {process.returncode}")

    return Remotes(remotes=[line.strip() for line in out.decode().splitlines() if line.strip()])


if __name__ == "__main__":
    # This starts a STDIO-based MCP server by default
    rclone_mcp.run()
