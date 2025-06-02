# AAA Issue Scanner

A command-line tool that uses OpenAI's o4-mini model to detect AAA (Arrange-Act-Assert) pattern issues in unit tests.

## Features

- 🔍 **Smart Detection**: Identifies 7 types of AAA pattern issues using AI
- 📊 **Batch Processing**: Process multiple test cases and generate CSV reports
- 💰 **Cost Tracking**: Track token usage and API costs with detailed breakdowns (enabled by default)
- 🚀 **Easy to Use**: Simple command-line interface with cross-platform support
- 📝 **Detailed Reports**: Provides analysis results and improvement suggestions

## Quick Start

### 1. Install & Setup

**With uv (Recommended):**
```bash
# Install uv if needed
pip install uv

# Clone and run (auto-manages dependencies)
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner

# Set API key
export OPENAI_API_KEY='your-openai-api-key'
```

**Traditional method:**
```bash
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner
pip install -e .
export OPENAI_API_KEY='your-openai-api-key'
```

### 2. Usage

**Single file analysis:**
```bash
# With uv (cost tracking enabled by default)
uv run python -m aaa_issue_scanner single test.json --verbose

# Traditional (cost tracking enabled by default)
python -m aaa_issue_scanner single test.json --verbose

# Disable cost tracking if desired
python -m aaa_issue_scanner single test.json --no-cost
```

**Batch processing:**
```bash
# With uv (cost tracking enabled by default)
uv run python -m aaa_issue_scanner batch project_folder

# Traditional (cost tracking enabled by default)
python -m aaa_issue_scanner batch project_folder

# Disable cost tracking if desired  
python -m aaa_issue_scanner batch project_folder --no-cost
```

## Installation Options

| Method | Command | Pros |
|--------|---------|------|
| **uv run** | `uv run python -m aaa_issue_scanner` | ✅ Auto-dependency management<br>✅ No installation needed |
| **uvx** | `uvx aaa-issue-scanner` | ✅ Global access<br>✅ Always latest version |
| **pip install** | `pip install -e .` | ✅ Traditional workflow<br>✅ System integration |

## API Key Setup

Get your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys).

**Environment Variable:**
```bash
# Unix/Linux/macOS
export OPENAI_API_KEY='your-key'

# Windows (Command Prompt)  
set OPENAI_API_KEY=your-key

# Windows (PowerShell)
$env:OPENAI_API_KEY='your-key'
```

**Or use CLI parameter:**
```bash
--api-key 'your-key'
```

## Input Format

JSON files with the following structure:
```json
{
  "parsedStatementsSequence": ["statement sequences"],
  "productionFunctionImplementations": ["production code"],
  "testCaseSourceCode": "test code string",
  "testClassName": "TestClass",
  "testCaseName": "testMethod",
  "projectName": "project-name",
  "beforeMethods": ["@Before methods"],
  "beforeAllMethods": ["@BeforeAll methods"],
  "afterMethods": ["@After methods"],
  "afterAllMethods": ["@AfterAll methods"]
}
```

## Batch Processing

**Project Structure:**
```
your_project/
├── AAA/                 # Required folder name
│   ├── test1.json      # Test files
│   ├── test2.json
│   └── test3.json
└── other_files...
```

**Enhanced Features:**
- ✅ **Multi-processing**: Concurrent processing with configurable workers
- ✅ **Smart Caching**: Automatically enabled to avoid reprocessing identical test cases
- ✅ **Smart Resume**: Automatically continues from where you left off (default behavior)
- ✅ **Rate Limiting**: Respect API limits with configurable requests per minute
- ✅ **Real-time Progress**: Live updates with detailed statistics

### 🚀 Multi-Threading Support

**Concurrent Processing:**
- **Auto-Detection**: Automatically uses multi-threading for batches with 2+ files
- **Configurable Workers**: Use `--max-workers` to control concurrency (default: 5)
- **Thread-Safe**: Rate limiting, cost tracking, and CSV writing are all thread-safe
- **Smart Fallback**: Falls back to single-threading for small batches or when `--max-workers 1`

**Usage Examples:**
```bash
# Default: 5 concurrent workers
python -m aaa_issue_scanner batch project_folder --verbose

# Use 8 workers for faster processing
python -m aaa_issue_scanner batch project_folder --max-workers 8 --verbose

# Force single-threaded processing
python -m aaa_issue_scanner batch project_folder --max-workers 1 --verbose
```

**Performance Benefits:**
- 🚀 **Faster Processing**: Up to N times faster with N workers (limited by API rate limits)
- 🔒 **Rate Limit Aware**: Respects OpenAI API rate limits even with multiple threads
- 💾 **Thread-Safe Caching**: Multiple threads can safely share cache without conflicts
- 📊 **Accurate Tracking**: Cost and progress tracking works correctly in multi-threaded mode

**Configuration Options:**
```bash
# Basic usage (caching and resume enabled by default)
python -m aaa_issue_scanner batch project_folder --verbose

# Advanced usage with custom settings
python -m aaa_issue_scanner batch project_folder \
    --max-workers 8 \
    --requests-per-minute 100 \
    --cache-dir .my_cache \
    --verbose

# Disable caching if needed (rare case)
python -m aaa_issue_scanner batch project_folder --no-cache --verbose

# Force restart from beginning (ignores previous progress)
python -m aaa_issue_scanner batch project_folder --restart --verbose
```

**Smart Caching (Default Enabled):**
- 🧠 **Content-based hashing**: Only identical test cases are cached
- 💾 **Persistent cache**: Survives between runs and projects
- 🚀 **Instant results**: Cached cases return immediately (no API call)
- 💰 **Cost savings**: Avoid redundant API charges for duplicate content
- 📁 **Custom location**: Use `--cache-dir` for custom cache folder
- ❌ **Override**: Use `--no-cache` only when you want fresh analysis for everything

**Simple Workflow (All Defaults Work Great):**
```bash
# Run once - caching and resume automatically enabled
python -m aaa_issue_scanner batch my_project --verbose

# If interrupted, just re-run the same command
python -m aaa_issue_scanner batch my_project --verbose
# ✅ Automatically resumes from where it left off
# ✅ Uses cache for any duplicate test cases
# ✅ No additional flags needed!
```

**Output:** CSV file with columns: `project`, `class_name`, `test_case_name`, `issue_type`, `sequence`, `focal_method`, `reasoning`

## Cost Tracking & Token Usage

The tool provides comprehensive cost tracking for OpenAI API usage:

### Supported Models & Pricing

| Model | Input ($/M tokens) | Cached Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------------|-------------------|
| **o4-mini** | $1.10 | $0.275 | $4.40 |
| **gpt-4.1** | $2.00 | $0.50 | $8.00 |
| **gpt-4.1-mini** | $0.40 | $0.10 | $1.60 |

### Usage Examples

**Single file with cost tracking (default behavior):**
```bash
python -m aaa_issue_scanner single test.json
```
Output includes:
```
💰 Cost Information:
   Input tokens: 1,127
   Output tokens: 764
   Total tokens: 1,891
   Total cost: $0.004601
```

**Batch processing with cost tracking (default behavior):**
```bash
python -m aaa_issue_scanner batch project_folder
```
Shows per-file costs and final summary:
```
💰 Cost Summary:
   Total API calls: 5
   Total tokens: 8,450
   - Input tokens: 5,635
   - Cached tokens: 1,024
   - Output tokens: 2,815
   
   Cost breakdown:
   - Input cost: $0.006199
   - Cached input cost: $0.000282
   - Output cost: $0.012386
   - Total cost: $0.018867
   - Cache savings: $0.000845
```

**Disable cost tracking if needed:**
```bash
python -m aaa_issue_scanner single test.json --no-cost
python -m aaa_issue_scanner batch project_folder --no-cost
```

### Cost Optimization Features

- **Smart Caching**: Identical test cases are cached, avoiding duplicate API calls
- **Cache Savings**: Shows how much money was saved through caching
- **Real-time Tracking**: See costs accumulate during batch processing
- **Model Flexibility**: Easily switch between models to optimize cost vs. quality

## Project Log Recording

The tool automatically maintains detailed project logs for tracking analysis history:

### Log File Format

Each project generates a `<project-name>-log.json` file in the **AAA folder** with:

```json
{
  "projectName": "commons-cli",
  "tasks": [
    {
      "taskName": "AAA-Pattern-Analysis",
      "model": "o4-mini",
      "timestamp": "2025-06-02T02:31:49.621123",
      "totalTestCases": 2,
      "processedTestCases": 2,
      "failedTestCases": 0,
      "cacheHits": 2,
      "apiCalls": 0,
      "tokenUsage": {
        "totalTokens": 0,
        "inputTokens": 0,
        "cachedTokens": 0,
        "outputTokens": 0,
        "avgTokensPerCall": 0
      },
      "costInfo": {
        "totalCost": 0.0,
        "inputCost": 0.0,
        "cachedInputCost": 0.0,
        "outputCost": 0.0,
        "cacheSavings": 0.0
      },
      "status": "COMPLETED"
    }
  ],
  "lastUpdated": "2025-06-02T02:31:49.621123"
}
```

### Log File Location

- **Path**: `<project-root>/AAA/<project-name>-log.json`
- **Example**: `my-project/AAA/my-project-log.json`
- **Automatic**: Creates or updates existing log files in the AAA folder
- **Multi-Project**: Each project maintains its own separate log file

### Log Features

- **Automatic Creation**: Creates or updates existing log files
- **Multi-Task Support**: Preserves other task entries (e.g., ParseTestCaseToLlmContext)
- **Complete Metrics**: Records test counts, success/failure rates, and cost details
- **Model Tracking**: Shows which AI model was used for analysis
- **Status Tracking**: `COMPLETED`, `COMPLETED_WITH_ERRORS`, or `IN_PROGRESS`
- **Historical Data**: Maintains analysis history across multiple runs

### 🚀 Interruption Recovery & Cost Tracking

**Smart Interruption Handling:**
- ✅ **Incremental Logging**: Updates project log every 3 processed files (not just at the end)
- ✅ **Cost Preservation**: Token usage and costs are saved even if the process is interrupted
- ✅ **Resume with Cost Accumulation**: When resuming, previous costs are loaded and accumulated
- ✅ **No Cost Loss**: Your API spending is tracked accurately across interruptions

**How it Works:**
```bash
# Start processing
python -m aaa_issue_scanner batch project_folder --verbose

# If interrupted (Ctrl+C, system crash, etc.), costs are already saved
# Resume processing - costs from previous session are automatically loaded
python -m aaa_issue_scanner batch project_folder --verbose
# Shows: "💾 Loaded previous session: X API calls, $Y.ZZ cost"
```

**Progress Tracking:**
- 📋 **Progress Files**: `.aaa_progress.json` tracks which files are completed
- 📝 **Project Logs**: `<project-name>-log.json` preserves cost and token information
- 🔄 **Smart Resume**: Skips processed files and accumulates previous costs
- 💾 **Frequent Saves**: Progress and costs updated every 3 files (prevents data loss)

## AAA Issue Types

| Issue Type | Description |
|------------|-------------|
| **Good AAA** | Proper AAA pattern |
| **Multiple AAA** | Multiple complete AAA sequences |
| **Missing Assert** | Test without assertions |
| **Assert Pre-condition** | Assertions before actions |
| **Obscure Assert** | Complex assertion logic |
| **Arrange & Quit** | Conditional early returns |
| **Multiple Acts** | Multiple sequential actions |
| **Suppressed Exception** | Exception suppression |

## Command Reference

### Single File Analysis
```bash
python -m aaa_issue_scanner single [OPTIONS] JSON_FILE

Options:
  --api-key TEXT                    OpenAI API key
  --model TEXT                      Model to use [default: o4-mini] 
  --reasoning-effort [low|medium|high]  Reasoning level [default: medium]
  -o, --output PATH                 Output file
  --no-cost                         Disable cost and token usage information
  -v, --verbose                     Verbose mode
```

### Batch Processing
```bash  
python -m aaa_issue_scanner batch [OPTIONS] PROJECT_ROOT

Options:
  --api-key TEXT                    OpenAI API key
  --model TEXT                      Model to use [default: o4-mini]
  --reasoning-effort [low|medium|high]  Reasoning level [default: medium]
  --max-workers INTEGER             Maximum concurrent workers [default: 5]
  --no-cache                        Disable caching (caching enabled by default)
  --restart                         Restart from beginning (ignore previous progress)  
  --cache-dir PATH                  Custom cache directory [default: .aaa_cache]
  --requests-per-minute INTEGER     Rate limit for API requests [default: 60]
  --no-cost                         Disable cost and token usage information
  -v, --verbose                     Verbose mode
```

## Platform-Specific Notes

### Windows
- **Path Support**: Automatically handles Windows path separators and long paths
- **File Names**: Automatically sanitizes CSV filenames for Windows compatibility  
- **Excel Compatibility**: CSV files use UTF-8 with BOM for proper Excel display
- **Cross-Platform Paths**: Uses `pathlib.Path` for full Windows/Unix path compatibility
- **Commands**: Use `py` instead of `python` if needed
- **PowerShell**: Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` if needed
- **File Permissions**: Ensure CSV output files aren't open in Excel when running batch processing

### Python Requirements
- Python 3.9 or higher
- Works with virtual environments and conda
- Automatically handles different line endings (LF, CRLF)

## Troubleshooting

**Common Issues:**

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3` or `py` |
| `Module not found` | Run `pip install -e .` in project directory |
| `Invalid API key` | Check key format (starts with `sk-` or `sk-proj-`) |
| `AAA folder not found` | Ensure `AAA/` folder exists in project root |
| `Permission denied` (Windows) | Close Excel/CSV files, run as Administrator |
| `Path too long` (Windows) | Enable long path support in Windows settings |
| `CSV garbled text` (Windows) | Tool uses UTF-8 with BOM automatically |

**Get Help:**
```bash
# Check installation
python -m aaa_issue_scanner --help

# Test with example
python -m aaa_issue_scanner single example_test.json --verbose
```

## Development

**Project Structure:**
```
src/aaa_issue_scanner/
├── cli.py              # Command-line interface
├── analyzer.py         # AAA analyzer  
├── formatter.py        # Data formatter
└── batch_processor.py  # Batch processing
```

**Run Tests:**
```bash
# Single file test
uv run python -m aaa_issue_scanner single example_test.json

# Batch test
uv run python -m aaa_issue_scanner batch test_project --verbose
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`) 
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

**Get your OpenAI API key:** [OpenAI Platform](https://platform.openai.com/api-keys)

**Report issues:** [GitHub Issues](https://github.com/your-username/AAA-Issue-Scanner/issues)