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

Make sure you have Python 3.9 or higher installed, then run:

```bash
# Clone the project
git clone https://github.com/your-username/AAA-Issue-Scanner.git
cd AAA-Issue-Scanner

# Install the project (development mode)
uv pip install -e .
```

## Quick Start

### 1. Set OpenAI API Key

The tool requires an OpenAI API key. You can get one from [OpenAI's platform](https://platform.openai.com/api-keys).

#### On Unix/Linux/macOS (Bash/Zsh):
```bash
export OPENAI_API_KEY='your-api-key-here'
```

#### On Windows (Command Prompt):
```cmd
set OPENAI_API_KEY=your-api-key-here
```

#### On Windows (PowerShell):
```powershell
$env:OPENAI_API_KEY='your-api-key-here'
```

#### Alternative: Using the CLI parameter
```bash
aaa-scanner --api-key 'your-api-key-here' your-file.json
```

### 2. Run Analysis

#### Single File Analysis (Backward Compatible)
```bash
# Analyze a single JSON file
python -m aaa_issue_scanner example_test.json

# Verbose mode
python -m aaa_issue_scanner example_test.json --verbose

# Save results to file
python -m aaa_issue_scanner example_test.json --output results.txt
```

#### Batch Processing (New!)
```bash
# Process all JSON files in project/AAA folder
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'project_root_path', '--verbose'])"

# Or using the CLI script (if installed globally)
aaa-scanner-cli batch project_root_path --verbose
```

## Batch Processing

The tool supports batch processing for analyzing multiple test cases at once:

### Project Structure Required
```
your_project/
├── AAA/                    # Required folder name
│   ├── test1.json         # Test case files
│   ├── test2.json
│   └── test3.json
└── other_project_files...
```

### Batch Processing Output
The tool will:
1. Process all `.json` files in the `AAA` folder
2. Generate a CSV file named `{project_name} AAA issue scan result.csv`
3. Save the CSV in the same `AAA` folder

### CSV Columns
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

## Command Line Usage

### Single File Mode
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

### Batch Processing Mode
```bash
# Using the CLI module
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'PROJECT_ROOT', '--verbose'])"

# Using installed script
aaa-scanner-cli batch PROJECT_ROOT [OPTIONS]

Options:
  --api-key TEXT              OpenAI API key
  --model TEXT                OpenAI model to use [default: o4-mini]
  --reasoning-effort [low|medium|high]  Reasoning effort level [default: medium]
  -v, --verbose               Verbose output mode
  --help                      Show this help message
```

## Examples

### Single File Analysis
```bash
python -m aaa_issue_scanner test_case.json --verbose
```

Output:
```
File loaded: test_case.json
Test case: testLongOptionQuoteHandling
Using model: o4-mini
API key: sk-1234...xy90
Calling OpenAI API...

=== AAA Pattern Analysis Results ===
<analysis>
  <focal_method>testLongOptionQuoteHandling</focal_method>
  <issueType>Good AAA</issueType>
  <sequence>Arrange → Act → Assert</sequence>
  <reasoning>
    This test follows the correct AAA pattern...
  </reasoning>
</analysis>
```

### Batch Processing
```bash
python -c "from src.aaa_issue_scanner.cli import cli; cli(['batch', 'my_project', '--verbose'])"
```

Output:
```
Project root: my_project
Using model: o4-mini
API key: sk-proj...DvUA

Found 3 JSON files in my_project/AAA
Processing: test1.json
Processing: test2.json
Processing: test3.json
Results saved to: my_project/AAA/commons-cli AAA issue scan result.csv
Processed 3 test cases successfully
Batch processing completed successfully! ✅
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

## Troubleshooting

### API Key Issues

If you encounter authentication errors:

1. **Check your API key format**: OpenAI keys typically start with `sk-` or `sk-proj-`
2. **Verify the key is valid**: Visit [OpenAI's platform](https://platform.openai.com/api-keys)
3. **Check environment variable**: 
   - Unix/Linux/macOS: `echo $OPENAI_API_KEY`
   - Windows CMD: `echo %OPENAI_API_KEY%`
   - Windows PowerShell: `echo $env:OPENAI_API_KEY`

### Batch Processing Issues

1. **"AAA folder not found"**: Ensure your project has an `AAA` folder in the root directory
2. **"No JSON files found"**: Check that the `AAA` folder contains `.json` files
3. **CSV generation fails**: Ensure write permissions to the `AAA` folder
4. **Parsing errors**: Check that JSON files follow the expected format

### Cross-Platform Notes

- **File paths**: Use forward slashes `/` or let the tool handle path conversion
- **Environment variables**: The tool automatically handles platform differences
- **Line endings**: JSON files with any line ending format (LF, CRLF) are supported

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Issues and improvement suggestions are welcome!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request