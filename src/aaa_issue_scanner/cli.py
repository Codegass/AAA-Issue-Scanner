#!/usr/bin/env python3
"""
AAA Issue Scanner CLI

A command-line tool for detecting AAA (Arrange-Act-Assert) pattern issues in unit tests.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import click
from openai import OpenAI

from .analyzer import AAAAnalyzer
from .formatter import TestCaseFormatter
from .batch_processor import BatchProcessor


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """AAA Issue Scanner - Detect AAA pattern issues in unit tests"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument('json_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--api-key', 
    envvar='OPENAI_API_KEY',
    help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)'
)
@click.option(
    '--model', 
    default='o4-mini',
    help='OpenAI model to use'
)
@click.option(
    '--reasoning-effort',
    default='medium',
    type=click.Choice(['low', 'medium', 'high']),
    help='Reasoning effort level'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file path (defaults to console output)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output mode'
)
def single(json_file: Path, api_key: str, model: str, reasoning_effort: str, output: Path, verbose: bool):
    """
    Analyze a single test case JSON file to detect AAA pattern issues.
    
    JSON_FILE: Path to JSON file containing test case data
    """
    
    if not _validate_api_key(api_key):
        return
    
    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        if verbose:
            click.echo(f"File loaded: {json_file}")
            click.echo(f"Test case: {test_data.get('testCaseName', 'Unknown')}")
            click.echo(f"Using model: {model}")
            click.echo(f"API key: {api_key[:7]}...{api_key[-4:] if len(api_key) > 11 else '***'}")
        
        # Format test data
        formatter = TestCaseFormatter()
        formatted_prompt = formatter.format_test_case(test_data)
        
        if verbose:
            click.echo("Calling OpenAI API...")
        
        # Call OpenAI API
        analyzer = AAAAnalyzer(api_key, model)
        result = analyzer.analyze(formatted_prompt, reasoning_effort)
        
        # Output results
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(result)
            click.echo(f"Analysis results saved to: {output}")
        else:
            click.echo("\n=== AAA Pattern Analysis Results ===")
            click.echo(result)
            
    except FileNotFoundError:
        click.echo(f"Error: File not found {json_file}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON format - {e}", err=True)
        sys.exit(1)
    except Exception as e:
        _handle_api_error(e)


@cli.command()
@click.argument('project_root', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    '--api-key', 
    envvar='OPENAI_API_KEY',
    help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)'
)
@click.option(
    '--model', 
    default='o4-mini',
    help='OpenAI model to use'
)
@click.option(
    '--reasoning-effort',
    default='medium',
    type=click.Choice(['low', 'medium', 'high']),
    help='Reasoning effort level'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output mode'
)
def batch(project_root: Path, api_key: str, model: str, reasoning_effort: str, verbose: bool):
    """
    Batch process all JSON files in the AAA folder of a project.
    
    PROJECT_ROOT: Path to the project root directory containing an AAA folder
    """
    
    if not _validate_api_key(api_key):
        return
    
    if verbose:
        click.echo(f"Project root: {project_root}")
        click.echo(f"Using model: {model}")
        click.echo(f"API key: {api_key[:7]}...{api_key[-4:] if len(api_key) > 11 else '***'}")
        click.echo("")
    
    try:
        # Create batch processor
        processor = BatchProcessor(api_key, model)
        
        # Process the project
        success = processor.process_project(project_root, reasoning_effort, verbose)
        
        if success:
            click.echo("Batch processing completed successfully! ✅")
        else:
            click.echo("Batch processing completed with errors ❌", err=True)
            sys.exit(1)
            
    except Exception as e:
        _handle_api_error(e)


# For backward compatibility, add the old main function as the default command
@click.command()
@click.argument('json_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--api-key', 
    envvar='OPENAI_API_KEY',
    help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)'
)
@click.option(
    '--model', 
    default='o4-mini',
    help='OpenAI model to use'
)
@click.option(
    '--reasoning-effort',
    default='medium',
    type=click.Choice(['low', 'medium', 'high']),
    help='Reasoning effort level'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file path (defaults to console output)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output mode'
)
def main(json_file: Path, api_key: str, model: str, reasoning_effort: str, output: Path, verbose: bool):
    """
    Analyze test cases in JSON file to detect AAA pattern issues.
    
    JSON_FILE: Path to JSON file containing test case data
    """
    # Call the single command function
    ctx = click.get_current_context()
    ctx.invoke(single, json_file=json_file, api_key=api_key, model=model, 
               reasoning_effort=reasoning_effort, output=output, verbose=verbose)


def _validate_api_key(api_key: str) -> bool:
    """Validate the API key and show helpful error messages if missing"""
    
    if not api_key:
        click.echo("Error: OpenAI API key not found", err=True)
        click.echo("", err=True)
        click.echo("Please set the OPENAI_API_KEY environment variable:", err=True)
        click.echo("", err=True)
        click.echo("On Unix/Linux/macOS:", err=True)
        click.echo("  export OPENAI_API_KEY='your-api-key-here'", err=True)
        click.echo("", err=True)
        click.echo("On Windows (Command Prompt):", err=True)
        click.echo("  set OPENAI_API_KEY=your-api-key-here", err=True)
        click.echo("", err=True)
        click.echo("On Windows (PowerShell):", err=True)
        click.echo("  $env:OPENAI_API_KEY='your-api-key-here'", err=True)
        click.echo("", err=True)
        click.echo("Alternatively, use the --api-key parameter:", err=True)
        click.echo("  aaa-scanner --api-key 'your-api-key-here' your-file.json", err=True)
        return False
    
    # Verify the API key format (basic validation)
    if not api_key.startswith(('sk-', 'sk-proj-')):
        click.echo("Warning: API key does not appear to be in the expected format", err=True)
        click.echo("OpenAI API keys typically start with 'sk-' or 'sk-proj-'", err=True)
        click.echo("")
    
    return True


def _handle_api_error(error: Exception):
    """Handle API-related errors with helpful messages"""
    
    error_msg = str(error)
    if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
        click.echo("Error: Invalid OpenAI API key", err=True)
        click.echo("Please check your API key and try again", err=True)
        click.echo("You can get an API key from: https://platform.openai.com/api-keys", err=True)
    else:
        click.echo(f"Error: {error}", err=True)
    sys.exit(1)


if __name__ == '__main__':
    main() 