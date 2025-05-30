"""
Batch Processor for AAA Issue Scanner

Handles batch processing of JSON files and CSV output generation.
"""

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import click

from .analyzer import AAAAnalyzer
from .formatter import TestCaseFormatter


class BatchProcessor:
    """Handles batch processing of test cases and CSV output generation"""
    
    def __init__(self, api_key: str, model: str = "o4-mini"):
        """
        Initialize batch processor
        
        Args:
            api_key: OpenAI API key
            model: Model name to use
        """
        self.analyzer = AAAAnalyzer(api_key, model)
        self.formatter = TestCaseFormatter()
        
    def process_project(self, project_root: Path, reasoning_effort: str = "medium", verbose: bool = False) -> bool:
        """
        Process all JSON files in the AAA folder of a project
        
        Args:
            project_root: Path to the project root directory
            reasoning_effort: Reasoning effort level
            verbose: Whether to output verbose information
            
        Returns:
            True if processing was successful, False otherwise
        """
        
        # Normalize path for cross-platform compatibility
        project_root = Path(project_root).resolve()
        aaa_folder = project_root / "AAA"
        
        if not aaa_folder.exists():
            click.echo(f"Error: AAA folder not found in {project_root}", err=True)
            click.echo("Please ensure there is an 'AAA' folder in the project root containing JSON files", err=True)
            return False
        
        if not aaa_folder.is_dir():
            click.echo(f"Error: AAA path exists but is not a directory: {aaa_folder}", err=True)
            return False
        
        # Find all JSON files
        json_files = list(aaa_folder.glob("*.json"))
        
        if not json_files:
            click.echo(f"Warning: No JSON files found in {aaa_folder}")
            return True
        
        if verbose:
            click.echo(f"Found {len(json_files)} JSON files in {aaa_folder}")
        
        # Get project name from the first file to create CSV
        project_name = None
        try:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                first_data = json.load(f)
                project_name = first_data.get('projectName', 'Unknown')
        except Exception:
            project_name = 'Unknown'
        
        # Create CSV file and write header
        csv_filename = self._sanitize_filename(f"{project_name} AAAResults.csv")
        csv_path = aaa_folder / csv_filename
        
        if not self._initialize_csv(csv_path, verbose):
            return False
        
        # Process each JSON file and update CSV incrementally
        processed_count = 0
        total_files = len(json_files)
        
        for i, json_file in enumerate(json_files, 1):
            if verbose:
                click.echo(f"Processing ({i}/{total_files}): {json_file.name}")
            
            try:
                result = self._process_single_file(json_file, reasoning_effort, verbose)
                if result:
                    # Immediately append to CSV
                    if self._append_to_csv(result, csv_path, verbose):
                        processed_count += 1
                        if verbose:
                            click.echo(f"  ✅ Added to CSV: {result['test_case_name']}")
                    else:
                        click.echo(f"  ❌ Failed to save result for {json_file.name}", err=True)
                else:
                    click.echo(f"  ⚠️ No result generated for {json_file.name}")
                        
            except Exception as e:
                click.echo(f"  ❌ Error processing {json_file.name}: {e}", err=True)
                continue
        
        if processed_count == 0:
            click.echo("No results were successfully processed", err=True)
            return False
        
        if verbose:
            click.echo(f"\n📊 Results saved to: {csv_path}")
            click.echo(f"📈 Processed {processed_count}/{total_files} test cases successfully")
        
        return True
    
    def _process_single_file(self, json_file: Path, reasoning_effort: str, verbose: bool) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON file
        
        Args:
            json_file: Path to JSON file
            reasoning_effort: Reasoning effort level
            verbose: Whether to output verbose information
            
        Returns:
            Dictionary with processed result or None if failed
        """
        
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            # Format test data
            formatted_prompt = self.formatter.format_test_case(test_data)
            
            # Analyze with OpenAI
            analysis_result = self.analyzer.analyze(formatted_prompt, reasoning_effort)
            
            # Parse the analysis result
            parsed_result = self._parse_analysis_result(analysis_result)
            
            if not parsed_result:
                if verbose:
                    click.echo(f"Warning: Could not parse analysis result for {json_file.name}")
                return None
            
            # Combine with original test data
            result = {
                'project': test_data.get('projectName', 'Unknown'),
                'class_name': test_data.get('testClassName', 'Unknown'),
                'test_case_name': test_data.get('testCaseName', 'Unknown'),
                'issue_type': parsed_result.get('issueType', 'Unknown'),
                'sequence': parsed_result.get('sequence', 'Unknown'),
                'focal_method': parsed_result.get('focal_method', 'Unknown'),
                'reasoning': parsed_result.get('reasoning', 'Unknown')
            }
            
            return result
            
        except json.JSONDecodeError as e:
            if verbose:
                click.echo(f"JSON decode error in {json_file.name}: {e}")
            return None
        except Exception as e:
            if verbose:
                click.echo(f"Error processing {json_file.name}: {e}")
            return None
    
    def _parse_analysis_result(self, analysis_result: str) -> Optional[Dict[str, str]]:
        """
        Parse the XML analysis result from OpenAI
        
        Args:
            analysis_result: XML string from OpenAI
            
        Returns:
            Dictionary with parsed fields or None if parsing failed
        """
        
        try:
            # Try to find the analysis block
            analysis_start = analysis_result.find('<analysis>')
            analysis_end = analysis_result.find('</analysis>')
            
            if analysis_start == -1 or analysis_end == -1:
                return None
            
            analysis_xml = analysis_result[analysis_start:analysis_end + 11]  # +11 for </analysis>
            
            # Parse XML
            root = ET.fromstring(analysis_xml)
            
            result = {}
            
            # Extract each field
            for field in ['focal_method', 'issueType', 'sequence', 'reasoning']:
                element = root.find(field)
                if element is not None and element.text:
                    result[field] = element.text.strip()
                else:
                    result[field] = 'Unknown'
            
            return result
            
        except ET.ParseError:
            # Fallback to regex parsing if XML parsing fails
            return self._parse_analysis_result_regex(analysis_result)
        except Exception:
            return None
    
    def _parse_analysis_result_regex(self, analysis_result: str) -> Optional[Dict[str, str]]:
        """
        Fallback regex parsing for analysis result
        
        Args:
            analysis_result: Analysis result string
            
        Returns:
            Dictionary with parsed fields or None if parsing failed
        """
        
        try:
            result = {}
            
            # Define regex patterns for each field
            patterns = {
                'focal_method': r'<focal_method>(.*?)</focal_method>',
                'issueType': r'<issueType>(.*?)</issueType>',
                'sequence': r'<sequence>(.*?)</sequence>',
                'reasoning': r'<reasoning>(.*?)</reasoning>'
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, analysis_result, re.DOTALL)
                if match:
                    result[field] = match.group(1).strip()
                else:
                    result[field] = 'Unknown'
            
            return result if any(v != 'Unknown' for v in result.values()) else None
            
        except Exception:
            return None
    
    def _initialize_csv(self, csv_path: Path, verbose: bool) -> bool:
        """
        Initialize CSV file with headers
        
        Args:
            csv_path: Path to save CSV file
            verbose: Whether to output verbose information
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            fieldnames = ['project', 'class_name', 'test_case_name', 'issue_type', 'sequence', 'focal_method', 'reasoning']
            
            # Ensure parent directory exists
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create CSV file with header
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            
            if verbose:
                click.echo(f"📝 Created CSV file: {csv_path}")
            
            return True
            
        except Exception as e:
            click.echo(f"Error creating CSV file: {e}", err=True)
            return False
    
    def _append_to_csv(self, result: Dict[str, Any], csv_path: Path, verbose: bool) -> bool:
        """
        Append a single result to CSV file
        
        Args:
            result: Result dictionary to append
            csv_path: Path to CSV file
            verbose: Whether to output verbose information
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            fieldnames = ['project', 'class_name', 'test_case_name', 'issue_type', 'sequence', 'focal_method', 'reasoning']
            
            # Clean the result data
            cleaned_result = {}
            for key in fieldnames:
                value = result.get(key, '')
                if value is None:
                    cleaned_result[key] = ''
                elif isinstance(value, str):
                    # Remove problematic characters that might cause CSV issues
                    cleaned_result[key] = value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
                else:
                    cleaned_result[key] = str(value)
            
            # Append to existing CSV file
            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(cleaned_result)
            
            return True
            
        except PermissionError as e:
            click.echo(f"Error: Permission denied when saving to {csv_path}", err=True)
            click.echo("Please ensure the file is not open in another application", err=True)
            if verbose:
                click.echo(f"Details: {e}", err=True)
            return False
        except Exception as e:
            if verbose:
                click.echo(f"Error appending to CSV: {e}", err=True)
            return False

    def _save_to_csv(self, results: List[Dict[str, Any]], csv_path: Path, verbose: bool) -> bool:
        """
        Save results to CSV file with Windows compatibility
        
        Args:
            results: List of result dictionaries
            csv_path: Path to save CSV file
            verbose: Whether to output verbose information
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            fieldnames = ['project', 'class_name', 'test_case_name', 'issue_type', 'sequence', 'focal_method', 'reasoning']
            
            # Ensure parent directory exists
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use UTF-8 with BOM for better Windows Excel compatibility
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Clean data before writing
                for result in results:
                    cleaned_result = {}
                    for key, value in result.items():
                        # Handle None values and clean strings
                        if value is None:
                            cleaned_result[key] = ''
                        elif isinstance(value, str):
                            # Remove problematic characters that might cause CSV issues
                            cleaned_result[key] = value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
                        else:
                            cleaned_result[key] = str(value)
                    writer.writerow(cleaned_result)
            
            return True
            
        except PermissionError as e:
            click.echo(f"Error: Permission denied when saving to {csv_path}", err=True)
            click.echo("Please ensure the file is not open in another application and you have write permissions", err=True)
            if verbose:
                click.echo(f"Details: {e}", err=True)
            return False
        except OSError as e:
            click.echo(f"Error: Could not save file to {csv_path}", err=True)
            click.echo("Please check the path is valid and accessible", err=True)
            if verbose:
                click.echo(f"Details: {e}", err=True)
            return False
        except Exception as e:
            if verbose:
                click.echo(f"Error saving CSV: {e}", err=True)
            else:
                click.echo(f"Error saving CSV file", err=True)
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for Windows compatibility
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for Windows
        """
        # Remove invalid Windows characters
        filename = re.sub(r'[\\/:*?"<>|]', '', filename)
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Handle Windows reserved names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        if name_without_ext.upper() in reserved_names:
            filename = f"_{filename}"
        
        # Limit filename length (Windows has 255 char limit)
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_len = 255 - len(ext) - 1 if ext else 255
            filename = f"{name[:max_name_len]}.{ext}" if ext else name[:255]
        
        # Ensure we have a valid filename
        if not filename or filename in ('.', '..'):
            filename = 'aaa_scan_result.csv'
        
        return filename 