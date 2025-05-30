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
        
        # Process each JSON file
        results = []
        project_name = None
        
        for json_file in json_files:
            if verbose:
                click.echo(f"Processing: {json_file.name}")
            
            try:
                result = self._process_single_file(json_file, reasoning_effort, verbose)
                if result:
                    results.append(result)
                    if not project_name:
                        project_name = result.get('project', 'Unknown')
                        
            except Exception as e:
                click.echo(f"Error processing {json_file.name}: {e}", err=True)
                continue
        
        if not results:
            click.echo("No results to save", err=True)
            return False
        
        # Save results to CSV
        csv_filename = f"{project_name} AAA issue scan result.csv"
        csv_path = aaa_folder / csv_filename
        
        success = self._save_to_csv(results, csv_path, verbose)
        
        if success and verbose:
            click.echo(f"Results saved to: {csv_path}")
            click.echo(f"Processed {len(results)} test cases successfully")
        
        return success
    
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
    
    def _save_to_csv(self, results: List[Dict[str, Any]], csv_path: Path, verbose: bool) -> bool:
        """
        Save results to CSV file
        
        Args:
            results: List of result dictionaries
            csv_path: Path to save CSV file
            verbose: Whether to output verbose information
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            fieldnames = ['project', 'class_name', 'test_case_name', 'issue_type', 'sequence', 'focal_method', 'reasoning']
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
            return True
            
        except Exception as e:
            if verbose:
                click.echo(f"Error saving CSV: {e}", err=True)
            return False 