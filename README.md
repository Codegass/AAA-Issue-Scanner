# AAA Issue Scanner

A command-line tool that uses OpenAI's o4-mini model to detect AAA (Arrange-Act-Assert) pattern issues in unit tests.

## Features

- 🔍 **Smart Detection**: Identifies 7 types of AAA pattern issues using AI
- 📊 **Batch Processing**: Process multiple test cases and generate CSV reports
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
# With uv
uv run python -m aaa_issue_scanner single test.json --verbose

# Traditional
python -m aaa_issue_scanner single test.json --verbose
```

**Batch processing:**
```bash
# With uv
uv run python -m aaa_issue_scanner batch project_folder --verbose

# Traditional  
python -m aaa_issue_scanner batch project_folder --verbose
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

**Output:** CSV file with columns: `project`, `class_name`, `test_case_name`, `issue_type`, `sequence`, `focal_method`, `reasoning`

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
  -v, --verbose                     Verbose mode
```

### Batch Processing
```bash  
python -m aaa_issue_scanner batch [OPTIONS] PROJECT_ROOT

Options:
  --api-key TEXT                    OpenAI API key
  --model TEXT                      Model to use [default: o4-mini]
  --reasoning-effort [low|medium|high]  Reasoning level [default: medium]  
  -v, --verbose                     Verbose mode
```

## Platform-Specific Notes

### Windows
- Use `py` instead of `python` if needed
- For PowerShell: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Both Command Prompt and PowerShell supported

### Python Requirements
- Python 3.9 or higher
- Works with virtual environments and conda

## Troubleshooting

**Common Issues:**

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3` or `py` |
| `Module not found` | Run `pip install -e .` in project directory |
| `Invalid API key` | Check key format (starts with `sk-` or `sk-proj-`) |
| `AAA folder not found` | Ensure `AAA/` folder exists in project root |

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