import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Generic, TypedDict, TypeVar

from mcp.server.fastmcp import Context, FastMCP
from util import get_logger

logger = get_logger("mcp_logs")

rclone_mcp = FastMCP("rclone")


T = TypeVar("T")


@dataclass
class ResultWrapper(Generic[T]):
    """
    A generic wrapper for MCP tool results.

    Attributes:
        success: Whether the operation completed successfully.
        result: The detailed output of the operation.
    """

    success: bool
    result: T


@dataclass
class AboutReturn:
    """Storage usage statistics for an rclone remote."""

    total: str
    used: str
    free: str
    trashed: str


@rclone_mcp.tool()
async def listremotes(ctx: Context) -> ResultWrapper[list[str] | None]:
    """
    List all configured rclone remotes.

    Args:
        ctx: The MCP context object used for error reporting.

    Returns:
        ResultWrapper:
            - success=True and a list of remote names if the command succeeds.
            - success=False and None if the command fails.
    """

    process = await asyncio.create_subprocess_exec(
        "rclone", "listremotes", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    out, err = await process.communicate()

    if err:
        logger.error(err.decode().strip())
        await ctx.error(err.decode.strip())

    if process.returncode != 0:
        logger.error(f"rclone listremotes failed with code {process.returncode}")
        await ctx.error(f"rclone listremotes failed with code {process.returncode}")
        return ResultWrapper(False, None)

    return ResultWrapper(True, [line.strip() for line in out.decode().splitlines() if line.strip()])


@rclone_mcp.tool()
async def lsf(remote: str, path: str, ctx: Context) -> ResultWrapper[list[str] | None]:
    """
    List the contents of a given path on a specific rclone remote.

    Args:
        remote: The name of the rclone remote (e.g., "Sharepoint:").
        path: The directory path inside the remote to list (e.g., "/Documents/").
        ctx: The MCP context object used for error reporting.

    Returns:
        ResultWrapper:
            - success=True and a list of filenames/directories in the specified path if successful.
            - success=False and None if the command fails.
    """
    process = await asyncio.create_subprocess_exec(
        "rclone",
        "lsf",
        f"{remote}{path}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    out, err = await process.communicate()

    if err:
        logger.error(err.decode().strip())
        await ctx.error(err.decode().strip())

    if process.returncode != 0:
        logger.error(f"rclone lsf failed with code {process.returncode}")
        await ctx.error(f"rclone lsf failed with code {process.returncode}")
        return ResultWrapper(False, None)

    return ResultWrapper(True, out.decode().splitlines())


@rclone_mcp.tool()
async def about(remote: str, ctx: Context) -> ResultWrapper[AboutReturn | None]:
    """
    Retrieve storage usage information about a remote.

    Args:
        remote: The name of the rclone remote to query (e.g., "GoogleDrive:").
        ctx: The MCP context object used for error reporting.

    Returns:
        ResultWrapper:
            - success=True and an AboutReturn object containing total, used, free, and trashed storage.
            - success=False and None if the command fails.
    """
    process = await asyncio.create_subprocess_exec(
        "rclone",
        "about",
        f"{remote}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    out, err = await process.communicate()

    if err:
        logger.error(err.decode().strip())
        await ctx.error(err.decode().strip())

    if process.returncode != 0:
        logger.error(f"rclone about failed with code {process.returncode}")
        await ctx.error(f"rclone about failed with code {process.returncode}")
        return ResultWrapper(False, None)

    out_result = out.decode().splitlines()
    values = [" ".join(x[1:]) for x in (j.split() for j in out_result)]

    return ResultWrapper(True, AboutReturn(*values))


@rclone_mcp.tool()
async def copy(remote: str, local_path: str, remote_path: str, ctx: Context) -> ResultWrapper[None]:
    """
    Copy a local file or directory to a remote destination.

    Args:
        remote: The name of the rclone remote (e.g., "Sharepoint:").
        local_path: The path to the local file or directory to copy.
        remote_path: The target path inside the remote where the file/directory should be placed.
        ctx: The MCP context object used for error reporting.

    Returns:
        ResultWrapper:
            - success=True and None if the file/directory was copied successfully.
            - success=False and None if the copy operation failed.
    """
    process = await asyncio.create_subprocess_exec(
        "rclone",
        "copy",
        f"{local_path}",
        f"{remote}{remote_path}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    out, err = await process.communicate()

    if err:
        logger.error(err.decode().strip())
        await ctx.error(err.decode().strip())

    if process.returncode != 0:
        logger.error(f"rclone copy failed with code {process.returncode}")
        await ctx.error(f"rclone copy failed with code {process.returncode}")
        return ResultWrapper(False, None)

    return ResultWrapper(True, None)


if __name__ == "__main__":
    # This starts a STDIO-based MCP server by default
    rclone_mcp.run()
