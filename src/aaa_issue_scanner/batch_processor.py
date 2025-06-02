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
import hashlib
import time
from datetime import datetime
import concurrent.futures
import threading

from .analyzer import AAAAnalyzer
from .formatter import TestCaseFormatter
from .cost_calculator import CostCalculator, TokenUsage, CostInfo


class BatchProcessor:
    """Handles batch processing of test cases and CSV output generation"""
    
    def __init__(self, api_key: str, model: str = "o4-mini", max_workers: int = 5, 
                 use_cache: bool = False, cache_dir: Optional[Path] = None,
                 requests_per_minute: int = 60):
        """
        Initialize batch processor
        
        Args:
            api_key: OpenAI API key
            model: Model name to use
            max_workers: Maximum number of concurrent workers
            use_cache: Whether to enable caching
            cache_dir: Custom cache directory
            requests_per_minute: Rate limit for API requests
        """
        self.analyzer = AAAAnalyzer(api_key, model)
        self.formatter = TestCaseFormatter()
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.requests_per_minute = requests_per_minute
        self.min_request_interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0
        
        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.cwd() / ".aaa_cache"
        
        if self.use_cache:
            self.cache_dir.mkdir(exist_ok=True)
            self._load_cache()
        
        # Rate limiting
        self._last_request_time = 0
        self._request_lock = threading.Lock()
        
        # Progress tracking
        self._processed_files = set()
        self._failed_files = set()
        
        # Cost tracking
        self.cost_calculator = CostCalculator()
        
    def process_project(self, project_root: Path, reasoning_effort: str = "medium", verbose: bool = False, restart: bool = False) -> bool:
        """
        Process all JSON files in the AAA folder of a project
        
        Args:
            project_root: Path to the project root directory
            reasoning_effort: Reasoning effort level
            verbose: Whether to output verbose information
            restart: Whether to restart from beginning (ignore previous progress)
            
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
        
        # Filter out hidden files and progress files
        json_files = [f for f in json_files if not f.name.startswith('.') and not f.name.endswith('-progress.json')]
        
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
        
        # Load progress from previous run (unless restarting)
        if restart:
            # Clear previous progress
            self._processed_files = set()
            self._failed_files = set()
            progress_file = project_root / "AAA" / ".aaa_progress.json"
            if progress_file.exists():
                progress_file.unlink()  # Delete progress file
            if verbose:
                click.echo("🔄 Restart mode: Starting fresh (ignoring previous progress)")
        else:
            # Default behavior: resume from previous run
            progress = self._load_progress(project_root)
            self._processed_files = set(progress['processed'])
            self._failed_files = set(progress['failed'])
            
            # Load and accumulate previous cost information from log file
            self._load_previous_costs(project_root, verbose)
            
            # Filter files based on resume logic
            if progress['processed']:
                remaining_files = [f for f in json_files if f.name not in self._processed_files]
                if verbose:
                    skipped_count = len(json_files) - len(remaining_files)
                    if skipped_count > 0:
                        click.echo(f"📋 Resume mode: Skipping {skipped_count} already processed files")
                        if self.analyzer.cost_calculator.call_count > 0:
                            click.echo(f"💾 Restored previous costs: ${self.analyzer.cost_calculator.total_cost.total_cost:.6f}")
                json_files = remaining_files
        
        if not json_files:
            if not restart and self._processed_files:
                click.echo("✅ All files already processed!")
                # Still update log to ensure it's current
                total_processed = len(self._processed_files)
                total_files = len(list(aaa_folder.glob("*.json"))) - len([f for f in aaa_folder.glob("*.json") if f.name.startswith('.') or f.name.endswith('-progress.json')])
                self._update_project_log(project_root, total_processed, total_files, len(self._failed_files), 0, 0)
                return True
            else:
                click.echo(f"Warning: No JSON files found in {aaa_folder}")
                return True
        
        # Create CSV file and write header
        csv_filename = self._sanitize_filename(f"{project_name} AAAResults.csv")
        csv_path = aaa_folder / csv_filename
        
        # Initialize CSV (create new or append based on restart mode)
        if restart or not csv_path.exists():
            if not self._initialize_csv(csv_path, verbose):
                return False
        elif verbose:
            click.echo(f"📝 Appending to existing CSV file: {csv_path}")
        
        # Process each JSON file and update CSV incrementally
        processed_count = 0
        total_files = len(json_files) + len(self._processed_files)  # Include already processed files
        cache_hits = 0
        api_calls = 0
        
        for i, json_file in enumerate(json_files, 1):
            if verbose:
                click.echo(f"Processing ({i}/{len(json_files)}): {json_file.name}")
            
            try:
                result = self._process_single_file(json_file, reasoning_effort, verbose)
                if result:
                    # Check if this was a cache hit
                    if result.get('_cache_hit'):
                        cache_hits += 1
                        if verbose:
                            click.echo(f"  💾 Cache hit: {result['test_case_name']}")
                    else:
                        api_calls += 1
                        if verbose:
                            # Show per-call cost info in verbose mode
                            call_cost = result.get('_cost_info')
                            usage_info = result.get('_usage_info')
                            if call_cost and usage_info:
                                click.echo(f"  💰 Cost: ${call_cost.total_cost:.6f} ({usage_info.input_tokens} in, {usage_info.completion_tokens} out)")
                    
                    # Immediately append to CSV
                    if self._append_to_csv(result, csv_path, verbose):
                        processed_count += 1
                        self._processed_files.add(json_file.name)
                        if verbose and not result.get('_cache_hit'):
                            click.echo(f"  ✅ Added to CSV: {result['test_case_name']}")
                    else:
                        click.echo(f"  ❌ Failed to save result for {json_file.name}", err=True)
                        self._failed_files.add(json_file.name)
                else:
                    click.echo(f"  ⚠️ No result generated for {json_file.name}")
                    self._failed_files.add(json_file.name)
                        
            except Exception as e:
                click.echo(f"  ❌ Error processing {json_file.name}: {e}", err=True)
                self._failed_files.add(json_file.name)
                continue
            
            # Save progress and update log every 3 files (more frequent updates)
            if (i % 3) == 0:
                self._save_progress(project_root, list(self._processed_files), list(self._failed_files))
                # Update log incrementally to prevent cost loss on interruption
                current_processed = len(self._processed_files)
                self._update_project_log(project_root, current_processed, total_files, len(self._failed_files), api_calls, cache_hits, incremental=True)
                if verbose:
                    click.echo(f"  💾 Progress saved ({current_processed} files processed)")
        
        if processed_count == 0 and len(self._processed_files) == 0:
            click.echo("No results were successfully processed", err=True)
            return False
        
        total_processed = len(self._processed_files)
        
        if verbose:
            click.echo(f"\n📊 Results saved to: {csv_path}")
            click.echo(f"📈 Processed {total_processed}/{total_files} test cases successfully")
            if self.use_cache and cache_hits > 0:
                click.echo(f"💾 Cache hits: {cache_hits}/{processed_count} ({cache_hits/processed_count*100:.1f}%)" if processed_count > 0 else f"💾 Cache hits: {cache_hits}")
            if api_calls > 0 or self.analyzer.cost_calculator.call_count > 0:
                total_api_calls = self.analyzer.cost_calculator.call_count
                click.echo(f"🌐 API calls: {total_api_calls} total")
            if self._failed_files:
                click.echo(f"⚠️ Failed files: {len(self._failed_files)}")
            
            # Show cost summary in verbose mode
            if self.analyzer.cost_calculator.call_count > 0:
                cost_summary = self.analyzer.get_cost_summary(verbose=True)
                click.echo(cost_summary)
        
        # Final update to project log
        self._update_project_log(project_root, total_processed, total_files, len(self._failed_files), api_calls, cache_hits, incremental=False)
        
        # Save final progress
        self._save_progress(project_root, list(self._processed_files), list(self._failed_files))
        
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
            
            # Check cache first
            content_hash = self._get_content_hash(test_data)
            cached_result = self._get_cached_result(content_hash)
            
            if cached_result:
                # Use cached result
                result = {
                    'project': test_data.get('projectName', 'Unknown'),
                    'class_name': test_data.get('testClassName', 'Unknown'),
                    'test_case_name': test_data.get('testCaseName', 'Unknown'),
                    'issue_type': cached_result.get('issueType', 'Unknown'),
                    'sequence': cached_result.get('sequence', 'Unknown'),
                    'focal_method': cached_result.get('focal_method', 'Unknown'),
                    'reasoning': cached_result.get('reasoning', 'Unknown'),
                    '_cache_hit': True  # Mark as cache hit
                }
                return result
            
            # Apply rate limiting before API call
            self._rate_limit()
            
            # Format test data
            formatted_prompt = self.formatter.format_test_case(test_data)
            
            # Analyze with OpenAI and get cost info
            analysis_result, usage, cost_info = self.analyzer.analyze_with_cost(formatted_prompt, reasoning_effort)
            
            # Track cost in batch processor
            self.cost_calculator.add_usage(usage, cost_info)
            
            # Parse the analysis result
            parsed_result = self._parse_analysis_result(analysis_result)
            
            if not parsed_result:
                if verbose:
                    click.echo(f"Warning: Could not parse analysis result for {json_file.name}")
                return None
            
            # Cache the parsed result
            self._cache_result(content_hash, parsed_result)
            
            # Combine with original test data
            result = {
                'project': test_data.get('projectName', 'Unknown'),
                'class_name': test_data.get('testClassName', 'Unknown'),
                'test_case_name': test_data.get('testCaseName', 'Unknown'),
                'issue_type': parsed_result.get('issueType', 'Unknown'),
                'sequence': parsed_result.get('sequence', 'Unknown'),
                'focal_method': parsed_result.get('focal_method', 'Unknown'),
                'reasoning': parsed_result.get('reasoning', 'Unknown'),
                '_cache_hit': False,  # Mark as fresh result
                '_cost_info': cost_info,  # Include cost info for verbose display
                '_usage_info': usage  # Include usage info for cost display
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

    def _load_cache(self):
        """Load cache from disk"""
        self.cache_file = self.cache_dir / "analysis_cache.json"
        self.cache = {}
        
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        if not self.use_cache:
            return
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass  # Ignore cache save errors
    
    def _get_content_hash(self, test_data: Dict[str, Any]) -> str:
        """Generate hash for test case content"""
        # Create a stable hash based on the test content
        content = {
            'testCaseSourceCode': test_data.get('testCaseSourceCode', ''),
            'parsedStatementsSequence': test_data.get('parsedStatementsSequence', []),
            'productionFunctionImplementations': test_data.get('productionFunctionImplementations', []),
            'beforeMethods': test_data.get('beforeMethods', []),
            'afterMethods': test_data.get('afterMethods', []),
            'beforeAllMethods': test_data.get('beforeAllMethods', []),
            'afterAllMethods': test_data.get('afterAllMethods', [])
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _get_cached_result(self, content_hash: str) -> Optional[Dict[str, str]]:
        """Get result from cache if available"""
        if not self.use_cache:
            return None
        return self.cache.get(content_hash)
    
    def _cache_result(self, content_hash: str, result: Dict[str, str]):
        """Cache analysis result"""
        if not self.use_cache:
            return
        
        self.cache[content_hash] = {
            **result,
            'cached_at': datetime.now().isoformat()
        }
        self._save_cache()
    
    def _rate_limit(self):
        """Apply rate limiting to API requests"""
        if self.min_request_interval <= 0:
            return
        
        with self._request_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()

    def _load_progress(self, project_root: Path) -> Dict[str, Any]:
        """Load progress from previous run"""
        progress_file = project_root / "AAA" / ".aaa_progress.json"
        
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {'processed': [], 'failed': []}
    
    def _save_progress(self, project_root: Path, processed: List[str], failed: List[str]):
        """Save current progress"""
        progress_file = project_root / "AAA" / ".aaa_progress.json"
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed': processed,
                    'failed': failed,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception:
            pass  # Ignore progress save errors
    
    def _load_previous_costs(self, project_root: Path, verbose: bool):
        """
        Load previous cost information from project log and accumulate to current session
        
        Args:
            project_root: Path to the project root directory
            verbose: Whether to output verbose information
        """
        
        try:
            # Determine project name and log file path
            project_name = "unknown-project"
            aaa_folder = project_root / "AAA"
            
            if aaa_folder.exists():
                json_files = list(aaa_folder.glob("*.json"))
                json_files = [f for f in json_files if not f.name.startswith('.') and not f.name.endswith('-progress.json')]
                if json_files:
                    try:
                        with open(json_files[0], 'r', encoding='utf-8') as f:
                            first_data = json.load(f)
                            project_name = first_data.get('projectName', project_root.name)
                    except Exception:
                        project_name = project_root.name
                else:
                    project_name = project_root.name
            else:
                project_name = project_root.name
            
            log_filename = f"{project_name}-log.json"
            log_path = project_root / log_filename
            
            if not log_path.exists():
                return  # No previous log to load from
            
            # Load existing log
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Find the most recent AAA analysis task
            aaa_task = None
            for task in log_data.get('tasks', []):
                if task.get('taskName') == 'AAA-Pattern-Analysis':
                    aaa_task = task
                    break
            
            if not aaa_task:
                return  # No previous AAA analysis to load from
            
            # Extract cost information
            token_usage = aaa_task.get('tokenUsage', {})
            cost_info = aaa_task.get('costInfo', {})
            
            # Create TokenUsage and CostInfo objects from the log data
            usage = TokenUsage(
                prompt_tokens=token_usage.get('inputTokens', 0) + token_usage.get('cachedTokens', 0),
                completion_tokens=token_usage.get('outputTokens', 0),
                total_tokens=token_usage.get('totalTokens', 0),
                cached_tokens=token_usage.get('cachedTokens', 0)
            )
            
            cost = CostInfo(
                input_cost=cost_info.get('inputCost', 0.0),
                cached_input_cost=cost_info.get('cachedInputCost', 0.0),
                output_cost=cost_info.get('outputCost', 0.0),
                total_cost=cost_info.get('totalCost', 0.0)
            )
            
            # Add to current cost calculator
            previous_calls = aaa_task.get('apiCalls', 0)
            if previous_calls > 0:
                self.analyzer.cost_calculator.total_usage.prompt_tokens += usage.prompt_tokens
                self.analyzer.cost_calculator.total_usage.completion_tokens += usage.completion_tokens
                self.analyzer.cost_calculator.total_usage.total_tokens += usage.total_tokens
                self.analyzer.cost_calculator.total_usage.cached_tokens += usage.cached_tokens
                
                self.analyzer.cost_calculator.total_cost.input_cost += cost.input_cost
                self.analyzer.cost_calculator.total_cost.cached_input_cost += cost.cached_input_cost
                self.analyzer.cost_calculator.total_cost.output_cost += cost.output_cost
                self.analyzer.cost_calculator.total_cost.total_cost += cost.total_cost
                
                self.analyzer.cost_calculator.call_count += previous_calls
                
                if verbose:
                    click.echo(f"💾 Loaded previous session: {previous_calls} API calls, ${cost.total_cost:.6f} cost")
                    
        except Exception as e:
            if verbose:
                click.echo(f"⚠️ Warning: Could not load previous costs: {e}")
            # Don't fail the process if cost loading fails
            pass

    def _update_project_log(self, project_root: Path, processed_count: int, total_files: int, 
                           failed_count: int, api_calls: int, cache_hits: int, incremental: bool = False):
        """
        Update the project log file with AAA analysis information
        
        Args:
            project_root: Path to the project root directory
            processed_count: Number of successfully processed test cases
            total_files: Total number of test files found
            failed_count: Number of failed test cases
            api_calls: Number of API calls made (current session only)
            cache_hits: Number of cache hits (current session only)
            incremental: Whether this is an incremental update
        """
        
        try:
            # Determine project name from first JSON file or use directory name
            project_name = "unknown-project"
            aaa_folder = project_root / "AAA"
            
            if aaa_folder.exists():
                json_files = list(aaa_folder.glob("*.json"))
                json_files = [f for f in json_files if not f.name.startswith('.') and not f.name.endswith('-progress.json')]
                if json_files:
                    try:
                        with open(json_files[0], 'r', encoding='utf-8') as f:
                            first_data = json.load(f)
                            project_name = first_data.get('projectName', project_root.name)
                    except Exception:
                        project_name = project_root.name
                else:
                    project_name = project_root.name
            else:
                project_name = project_root.name
            
            # Construct log file path
            log_filename = f"{project_name}-log.json"
            log_path = project_root / log_filename
            
            # Load existing log or create new one
            log_data = {}
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                except Exception:
                    # If file is corrupted, start fresh
                    log_data = {}
            
            # Get cost data from analyzer (includes accumulated costs from previous sessions)
            cost_summary = self.analyzer.get_cost_data()
            
            # Get current timestamp
            current_time = datetime.now().isoformat()
            
            # Create AAA analysis entry
            status = "COMPLETED" if failed_count == 0 else "COMPLETED_WITH_ERRORS"
            if incremental and processed_count < total_files:
                status = "IN_PROGRESS"
            
            aaa_analysis_entry = {
                "taskName": "AAA-Pattern-Analysis",
                "model": self.analyzer.model,
                "timestamp": current_time,
                "totalTestCases": total_files,
                "processedTestCases": processed_count,
                "failedTestCases": failed_count,
                "cacheHits": cache_hits,
                "apiCalls": cost_summary.get("total_calls", 0),  # Total calls including previous sessions
                "tokenUsage": {
                    "totalTokens": cost_summary.get("total_tokens", 0),
                    "inputTokens": cost_summary.get("prompt_tokens", 0) - cost_summary.get("cached_tokens", 0),
                    "cachedTokens": cost_summary.get("cached_tokens", 0),
                    "outputTokens": cost_summary.get("completion_tokens", 0),
                    "avgTokensPerCall": cost_summary.get("avg_tokens_per_call", 0)
                },
                "costInfo": {
                    "totalCost": cost_summary.get("total_cost", 0.0),
                    "inputCost": cost_summary.get("input_cost", 0.0),
                    "cachedInputCost": cost_summary.get("cached_input_cost", 0.0),
                    "outputCost": cost_summary.get("output_cost", 0.0),
                    "cacheSavings": cost_summary.get("cache_savings", 0.0)
                },
                "status": status
            }
            
            # Ensure log data has required structure
            if "projectName" not in log_data:
                log_data["projectName"] = project_name
            
            # Add or update AAA analysis tasks
            if "tasks" not in log_data:
                log_data["tasks"] = []
            
            # Check if there's already an AAA analysis entry and update it
            aaa_task_found = False
            for i, task in enumerate(log_data["tasks"]):
                if task.get("taskName") == "AAA-Pattern-Analysis":
                    log_data["tasks"][i] = aaa_analysis_entry
                    aaa_task_found = True
                    break
            
            # If no existing AAA task, append new one
            if not aaa_task_found:
                log_data["tasks"].append(aaa_analysis_entry)
            
            # Update project-level summary if needed
            log_data["lastUpdated"] = current_time
            
            # Save updated log
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            if not incremental:  # Only show message for final updates
                click.echo(f"📋 Updated project log: {log_path}")
            
        except Exception as e:
            # Don't fail the whole process if logging fails
            click.echo(f"⚠️ Warning: Could not update project log: {e}") 