# AAA Issue Scanner

A command-line tool for detecting AAA (Arrange-Act-Assert) pattern issues in unit tests.

## Features

- 🔍 **Smart Detection**: Uses OpenAI's o4-mini model to analyze test code
- 🎯 **Multiple Issue Types**: Detects 7 different types of AAA pattern issues
- 📝 **Detailed Reports**: Provides detailed analysis results and improvement suggestions
- 🚀 **Easy to Use**: Simple command-line interface
- 💾 **Flexible Output**: Supports console output and file saving
- 🌐 **Cross-Platform**: Works on Windows, macOS, and Linux
- 📊 **Batch Processing**: Process multiple test cases and generate CSV reports
- 🔄 **Two Modes**: Single file analysis or batch processing of entire projects

## Installation

### Prerequisites
- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **Git** (optional) - [Download Git](https://git-scm.com/downloads)

### Option 1: Quick Install (Recommended)

#### On Windows:
1. **Open Command Prompt or PowerShell as Administrator**
2. **Install uv (Python package manager):**
   ```cmd
   # In Command Prompt
   pip install uv
   
   # Or in PowerShell
   pip install uv
   ```
3. **Clone and install the project:**
   ```cmd
   # Clone the repository
   git clone https://github.com/your-username/AAA-Issue-Scanner.git
   cd AAA-Issue-Scanner
   
   # Install with uv
   uv pip install -e .
   ```

#### On macOS/Linux:
```bash
# Install uv
pip install uv

# Clone and install
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner
uv pip install -e .
```

### Option 2: Alternative Install (Without uv)

#### On Windows:
```cmd
# Clone the repository
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner

# Create virtual environment
python -m venv venv

# Activate virtual environment
# In Command Prompt:
venv\Scripts\activate
# In PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install -e .
```

#### On macOS/Linux:
```bash
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Quick Start Guide

### Step 1: Get Your OpenAI API Key

1. Visit [OpenAI's platform](https://platform.openai.com/api-keys)
2. Sign up or log in to your account
3. Create a new API key
4. Copy the key (it starts with `sk-` or `sk-proj-`)

### Step 2: Set Up Your API Key

Choose **ONE** of the following methods:

#### Method A: Environment Variable (Recommended)

**On Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY='your-api-key-here'
```

**On macOS/Linux:**
```bash
export OPENAI_API_KEY='your-api-key-here'
```

#### Method B: Use CLI Parameter
Add `--api-key your-api-key-here` to any command.

### Step 3: Test the Installation

Create a test JSON file or use the provided example:

**On Windows:**
```cmd
# Test single file analysis
python -m aaa_issue_scanner example_test.json --verbose
```

**On macOS/Linux:**
```bash
# Test single file analysis
python -m aaa_issue_scanner example_test.json --verbose
```

If you see analysis results, congratulations! 🎉 The tool is working correctly.

## Usage

### Single File Analysis

**Windows Example:**
```cmd
# Basic analysis
python -m aaa_issue_scanner my_test.json

# Verbose output
python -m aaa_issue_scanner my_test.json --verbose

# Save to file
python -m aaa_issue_scanner my_test.json --output results.txt

# Use specific API key
python -m aaa_issue_scanner my_test.json --api-key sk-your-key-here
```

**macOS/Linux Example:**
```bash
# Same commands work on Unix systems
python -m aaa_issue_scanner my_test.json --verbose
```

### Batch Processing

For analyzing multiple test cases at once:

#### Step 1: Organize Your Files
Create this folder structure:
```
your_project/
├── AAA/                    # Must be named "AAA"
│   ├── test1.json         # Your test case files
│   ├── test2.json
│   └── test3.json
└── other_files...
```

#### Step 2: Run Batch Analysis

**On Windows (Command Prompt):**
```cmd
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'your_project', '--verbose'])"
```

**On Windows (PowerShell):**
```powershell
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'your_project', '--verbose'])"
```

**On macOS/Linux:**
```bash
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'your_project', '--verbose'])"
```

#### Step 3: Check Results
Look for the CSV file in `your_project/AAA/{project_name} AAA issue scan result.csv`

## Windows-Specific Tips

### PowerShell Execution Policy
If you get execution policy errors in PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Long Path Support
For very long file paths on Windows 10/11:
1. Open Group Policy Editor (`gpedit.msc`)
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"

### Alternative Python Commands
If `python` doesn't work, try:
```cmd
py -m aaa_issue_scanner example_test.json
# or
python3 -m aaa_issue_scanner example_test.json
```

### Virtual Environment on Windows
To avoid conflicts with other Python projects:
```cmd
# Create virtual environment
python -m venv aaa_scanner_env

# Activate it
aaa_scanner_env\Scripts\activate

# Install the scanner
pip install -e .

# When done, deactivate
deactivate
```

## Troubleshooting

### Common Issues

#### "Python not found" on Windows
1. Reinstall Python from [python.org](https://python.org)
2. ✅ Check "Add Python to PATH" during installation
3. Restart Command Prompt/PowerShell

#### "Module not found" Error
```cmd
# Make sure you're in the right directory
cd path\to\AAA-Issue-Scanner

# Reinstall
pip install -e .
```

#### API Key Issues
1. **Invalid format**: Keys should start with `sk-` or `sk-proj-`
2. **Not set**: Run `echo %OPENAI_API_KEY%` (Windows) or `echo $OPENAI_API_KEY` (Unix)
3. **Expired**: Check your OpenAI account and regenerate the key

#### "AAA folder not found"
Make sure your project structure looks like:
```
project_root/
├── AAA/           ← This folder must exist
│   └── *.json     ← JSON files go here
```

### Getting Help

If you're still having issues:

1. **Check your Python version:**
   ```cmd
   python --version
   ```
   Should show 3.9 or higher.

2. **Verify installation:**
   ```cmd
   python -m aaa_issue_scanner --help
   ```

3. **Test with verbose mode:**
   ```cmd
   python -m aaa_issue_scanner example_test.json --verbose
   ```

## Input Format

The tool accepts JSON files containing the following fields:

```json
{
  "parsedStatementsSequence": ["array of statement sequences"],
  "productionFunctionImplementations": ["array of production code implementations"],
  "testCaseSourceCode": "test code string",
  "importedPackages": ["array of imported packages"],
  "testClassName": "test class name",
  "testCaseName": "test method name",
  "projectName": "project name",
  "beforeMethods": ["array of @Before/@BeforeEach methods"],
  "beforeAllMethods": ["array of @BeforeAll methods"],
  "afterMethods": ["array of @After/@AfterEach methods"],
  "afterAllMethods": ["array of @AfterAll methods"]
}
```

## AAA Issue Types Detected

### Structural Issues
1. **Multiple AAA**: Test contains multiple complete AAA sequences
2. **Missing Assert**: Test without assertions
3. **Assert Pre-condition**: Assertions before actions

### Design Issues
4. **Obscure Assert**: Complex assertion logic
5. **Arrange & Quit**: Conditional early returns
6. **Multiple Acts**: Multiple sequential actions
7. **Suppressed Exception**: Exception suppression

## Batch Processing Details

### CSV Output Columns
| Column | Description |
|--------|-------------|
| project | Project name from JSON |
| class_name | Test class name |
| test_case_name | Test method name |
| issue_type | AAA issue type (e.g., "Good AAA", "Multiple AAA") |
| sequence | Pattern sequence found |
| focal_method | Main method being tested |
| reasoning | Detailed analysis explanation |

### Example CSV Output
```csv
project,class_name,test_case_name,issue_type,sequence,focal_method,reasoning
commons-cli,AbstractParserTestCase,testLongOptionQuoteHandling,Good AAA,Arrange → Act → Assert,CommandLineParser.parse,"The test sets up its input arguments (Arrange)..."
commons-cli,BasicParserTest,testSimpleOption,Good AAA,Arrange → Act → Assert,CommandLineParser.parse,"The test sets up its preconditions..."
```

## Advanced Usage

### Command Line Options

#### Single File Mode
```bash
python -m aaa_issue_scanner [OPTIONS] JSON_FILE

Options:
  --api-key TEXT              OpenAI API key
  --model TEXT                OpenAI model to use [default: o4-mini]
  --reasoning-effort [low|medium|high]  Reasoning effort level [default: medium]
  -o, --output PATH           Output file path
  -v, --verbose               Verbose output mode
  --help                      Show this help message
```

#### Batch Processing Mode
```bash
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'PROJECT_ROOT', '--verbose'])"

Options:
  --api-key TEXT              OpenAI API key
  --model TEXT                OpenAI model to use [default: o4-mini]
  --reasoning-effort [low|medium|high]  Reasoning effort level [default: medium]
  -v, --verbose               Verbose output mode
  --help                      Show this help message
```

## Environment Variables

The tool recognizes the following environment variable:

- `OPENAI_API_KEY`: Your OpenAI API key (required)

This works across all platforms:
- **Unix/Linux/macOS**: Automatically read from shell environment
- **Windows**: Read from system environment variables
- **Python environments**: Compatible with virtual environments and conda

## Development

### Project Structure

```
src/aaa_issue_scanner/
├── __init__.py          # Package initialization
├── __main__.py          # Main entry point
├── cli.py               # Command-line interface
├── analyzer.py          # AAA analyzer
├── formatter.py         # Data formatter
└── batch_processor.py   # Batch processing and CSV generation
```

### Running Tests

```bash
# Test single file
python -m aaa_issue_scanner example_test.json

# Test batch processing (requires test_project/AAA/ with JSON files)
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'test_project', '--verbose'])"
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Issues and improvement suggestions are welcome!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request