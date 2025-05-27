#!/usr/bin/env python3
"""
XCTools MCP Server

A Model Context Protocol server that provides structured access to Xcode 
development tools including xcrun, xcodebuild, and xctrace.
"""
import asyncio
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP


# Initialize the MCP server
mcp = FastMCP("XCTools MCP Server")


class XCToolsError(Exception):
    """Base exception for XCTools MCP operations"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


async def run_command(cmd: List[str]) -> str:
    """Run a command and return the output"""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Command failed"
            raise XCToolsError(f"Command {' '.join(cmd)} failed: {error_msg}")
        
        return stdout.decode().strip()
    
    except FileNotFoundError as e:
        raise XCToolsError(f"Command not found: {cmd[0]}. Make sure Xcode is installed.")


# XCRUN Tools

@mcp.tool()
async def xcrun_find_tool(tool_name: str, sdk: Optional[str] = None) -> str:
    """
    Find the path to a development tool using xcrun.
    
    Args:
        tool_name: Name of the tool to find (e.g., 'clang', 'swift', 'texturetool')
        sdk: SDK name to search in (e.g., 'iphoneos', 'macosx')
        
    Returns:
        Absolute path to the tool
    """
    cmd = ["xcrun"]
    
    if sdk:
        cmd.extend(["--sdk", sdk])
    
    cmd.extend(["--find", tool_name])
    
    result = await run_command(cmd)
    return f"Tool '{tool_name}' found at: {result}"


@mcp.tool()
async def xcrun_show_sdk_path(sdk: Optional[str] = None) -> str:
    """
    Show the path to the SDK.
    
    Args:
        sdk: SDK name (e.g., 'iphoneos', 'macosx'). Uses default if not specified.
        
    Returns:
        Path to the SDK
    """
    cmd = ["xcrun"]
    
    if sdk:
        cmd.extend(["--sdk", sdk])
    
    cmd.append("--show-sdk-path")
    
    result = await run_command(cmd)
    return f"SDK path: {result}"


@mcp.tool()
async def xcrun_show_sdk_version(sdk: Optional[str] = None) -> str:
    """
    Show the version of the SDK.
    
    Args:
        sdk: SDK name (e.g., 'iphoneos', 'macosx'). Uses default if not specified.
        
    Returns:
        Version of the SDK
    """
    cmd = ["xcrun"]
    
    if sdk:
        cmd.extend(["--sdk", sdk])
    
    cmd.append("--show-sdk-version")
    
    result = await run_command(cmd)
    return f"SDK version: {result}"


@mcp.tool()
async def xcrun_run_tool(tool_name: str, args: List[str], sdk: Optional[str] = None, 
                        verbose: bool = False) -> str:
    """
    Run a development tool via xcrun.
    
    Args:
        tool_name: Name of the tool to run
        args: Arguments to pass to the tool
        sdk: SDK to use when running the tool
        verbose: Enable verbose output
        
    Returns:
        Output from the tool
    """
    cmd = ["xcrun"]
    
    if verbose:
        cmd.append("--verbose")
    
    if sdk:
        cmd.extend(["--sdk", sdk])
    
    cmd.append(tool_name)
    cmd.extend(args)
    
    result = await run_command(cmd)
    return result


# XCODEBUILD Tools

@mcp.tool()
async def xcodebuild_build(project: Optional[str] = None, workspace: Optional[str] = None,
                          scheme: Optional[str] = None, target: Optional[str] = None,
                          configuration: Optional[str] = None, sdk: Optional[str] = None,
                          destination: Optional[str] = None, clean: bool = False) -> str:
    """
    Build an Xcode project or workspace.
    
    Args:
        project: Path to .xcodeproj file
        workspace: Path to .xcworkspace file
        scheme: Scheme name to build
        target: Target name to build
        configuration: Build configuration (Debug, Release, etc.)
        sdk: SDK to build against
        destination: Destination to build for
        clean: Whether to clean before building
        
    Returns:
        Build output
    """
    cmd = ["xcodebuild"]
    
    if clean:
        cmd.append("clean")
    
    cmd.append("build")
    
    if project:
        cmd.extend(["-project", project])
    elif workspace:
        cmd.extend(["-workspace", workspace])
    
    if scheme:
        cmd.extend(["-scheme", scheme])
    elif target:
        cmd.extend(["-target", target])
    
    if configuration:
        cmd.extend(["-configuration", configuration])
    
    if sdk:
        cmd.extend(["-sdk", sdk])
    
    if destination:
        cmd.extend(["-destination", destination])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xcodebuild_test(project: Optional[str] = None, workspace: Optional[str] = None,
                         scheme: str = None, destination: Optional[str] = None,
                         test_plan: Optional[str] = None, only_testing: List[str] = None,
                         skip_testing: List[str] = None) -> str:
    """
    Run tests for an Xcode project or workspace.
    
    Args:
        project: Path to .xcodeproj file
        workspace: Path to .xcworkspace file  
        scheme: Scheme name to test (required)
        destination: Destination to test on
        test_plan: Name of test plan to use
        only_testing: List of test identifiers to run exclusively
        skip_testing: List of test identifiers to skip
        
    Returns:
        Test results
    """
    if not scheme:
        raise XCToolsError("scheme is required for testing")
    
    cmd = ["xcodebuild", "test"]
    
    if project:
        cmd.extend(["-project", project])
    elif workspace:
        cmd.extend(["-workspace", workspace])
    
    cmd.extend(["-scheme", scheme])
    
    if destination:
        cmd.extend(["-destination", destination])
    
    if test_plan:
        cmd.extend(["-testPlan", test_plan])
    
    if only_testing:
        for test in only_testing:
            cmd.extend(["-only-testing", test])
    
    if skip_testing:
        for test in skip_testing:
            cmd.extend(["-skip-testing", test])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xcodebuild_archive(project: Optional[str] = None, workspace: Optional[str] = None,
                            scheme: str = None, archive_path: str = None) -> str:
    """
    Archive an Xcode project or workspace.
    
    Args:
        project: Path to .xcodeproj file
        workspace: Path to .xcworkspace file
        scheme: Scheme name to archive (required)
        archive_path: Path where to save the archive
        
    Returns:
        Archive result
    """
    if not scheme:
        raise XCToolsError("scheme is required for archiving")
    
    cmd = ["xcodebuild", "archive"]
    
    if project:
        cmd.extend(["-project", project])
    elif workspace:
        cmd.extend(["-workspace", workspace])
    
    cmd.extend(["-scheme", scheme])
    
    if archive_path:
        cmd.extend(["-archivePath", archive_path])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xcodebuild_list(project: Optional[str] = None, workspace: Optional[str] = None) -> str:
    """
    List targets and configurations in a project, or schemes in a workspace.
    
    Args:
        project: Path to .xcodeproj file
        workspace: Path to .xcworkspace file
        
    Returns:
        List of targets/schemes and configurations
    """
    cmd = ["xcodebuild", "-list"]
    
    if project:
        cmd.extend(["-project", project])
    elif workspace:
        cmd.extend(["-workspace", workspace])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xcodebuild_show_sdks() -> str:
    """
    List all available SDKs.
    
    Returns:
        List of available SDKs
    """
    cmd = ["xcodebuild", "-showsdks"]
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xcodebuild_show_destinations(project: Optional[str] = None, workspace: Optional[str] = None,
                                      scheme: str = None) -> str:
    """
    List valid destinations for a project or workspace and scheme.
    
    Args:
        project: Path to .xcodeproj file
        workspace: Path to .xcworkspace file
        scheme: Scheme name (required)
        
    Returns:
        List of valid destinations
    """
    if not scheme:
        raise XCToolsError("scheme is required for showing destinations")
    
    cmd = ["xcodebuild", "-showdestinations"]
    
    if project:
        cmd.extend(["-project", project])
    elif workspace:
        cmd.extend(["-workspace", workspace])
    
    cmd.extend(["-scheme", scheme])
    
    result = await run_command(cmd)
    return result


# XCTRACE Tools

@mcp.tool()
async def xctrace_record(template: str, output_path: Optional[str] = None,
                        device: Optional[str] = None, time_limit: Optional[str] = None,
                        all_processes: bool = False, attach_process: Optional[str] = None,
                        launch_command: Optional[List[str]] = None) -> str:
    """
    Record a new Instruments trace using the specified template.
    
    Args:
        template: Template name or path to use for recording
        output_path: Path to save the trace file
        device: Device name or UDID to record on
        time_limit: Time limit for recording (e.g., '5s', '1m')
        all_processes: Record all processes on the system
        attach_process: Process name or PID to attach to
        launch_command: Command and arguments to launch and record
        
    Returns:
        Recording result
    """
    cmd = ["xctrace", "record", "--template", template]
    
    if output_path:
        cmd.extend(["--output", output_path])
    
    if device:
        cmd.extend(["--device", device])
    
    if time_limit:
        cmd.extend(["--time-limit", time_limit])
    
    if all_processes:
        cmd.append("--all-processes")
    elif attach_process:
        cmd.extend(["--attach", attach_process])
    elif launch_command:
        cmd.extend(["--launch", "--"] + launch_command)
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xctrace_import(input_file: str, template: str, output_path: Optional[str] = None,
                        instrument: Optional[str] = None, package: Optional[str] = None) -> str:
    """
    Import a supported file format into an Instruments trace file.
    
    Args:
        input_file: Path to the input file to import (e.g., .logarchive, .ktrace)
        template: Template name or path to use for import
        output_path: Path to save the imported trace file
        instrument: Name of instrument to add to import configuration
        package: Path to Instruments Package to install temporarily
        
    Returns:
        Import result
    """
    cmd = ["xctrace", "import", "--input", input_file, "--template", template]
    
    if output_path:
        cmd.extend(["--output", output_path])
    
    if instrument:
        cmd.extend(["--instrument", instrument])
    
    if package:
        cmd.extend(["--package", package])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xctrace_export(input_file: str, output_path: Optional[str] = None,
                        toc: bool = False, xpath: Optional[str] = None) -> str:
    """
    Export data from an Instruments trace file.
    
    Args:
        input_file: Path to the .trace file to export from
        output_path: Path to save the exported data
        toc: Export table of contents
        xpath: XPath expression to select specific data
        
    Returns:
        Exported data or success message
    """
    cmd = ["xctrace", "export", "--input", input_file]
    
    if output_path:
        cmd.extend(["--output", output_path])
    
    if toc:
        cmd.append("--toc")
    elif xpath:
        cmd.extend(["--xpath", xpath])
    
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xctrace_list(list_type: str) -> str:
    """
    List available devices, templates, or instruments.
    
    Args:
        list_type: What to list ('devices', 'templates', 'instruments')
        
    Returns:
        List of requested items
    """
    if list_type not in ['devices', 'templates', 'instruments']:
        raise XCToolsError("list_type must be 'devices', 'templates', or 'instruments'")
    
    cmd = ["xctrace", "list", list_type]
    result = await run_command(cmd)
    return result


@mcp.tool()
async def xctrace_symbolicate(input_file: str, output_path: Optional[str] = None,
                             dsym_path: Optional[str] = None) -> str:
    """
    Symbolicate a trace file using debug symbols.
    
    Args:
        input_file: Path to the .trace file to symbolicate
        output_path: Path to save the symbolicated trace
        dsym_path: Path to dSYM file or directory containing dSYMs
        
    Returns:
        Symbolication result
    """
    cmd = ["xctrace", "symbolicate", "--input", input_file]
    
    if output_path:
        cmd.extend(["--output", output_path])
    
    if dsym_path:
        cmd.extend(["--dsym", dsym_path])
    
    result = await run_command(cmd)
    return result


def cli():
    """CLI entry point for package installation"""
    mcp.run()


if __name__ == "__main__":
    mcp.run()
