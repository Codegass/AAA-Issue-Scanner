"""
AAA Pattern Analyzer

Uses OpenAI API to analyze AAA pattern issues in test cases.
"""

from typing import Optional, Tuple

from openai import OpenAI
from openai.types.chat import ChatCompletion

from .cost_calculator import CostCalculator, TokenUsage, CostInfo


class AAAAnalyzer:
    """Class responsible for calling OpenAI API to perform AAA pattern analysis"""
    
    # System prompt for AAA analysis
    SYSTEM_PROMPT = """You are an expert software testing analyzer specializing in detecting AAA (Arrange-Act-Assert) pattern issues in unit test code. 

## AAA Pattern Definition
The correct AAA pattern follows this sequence: Arrange → Act → Assert
- **Arrange**: Set up test data, mock objects, and preconditions
- **Act**: Execute the method/functionality being tested  
- **Assert**: Verify the expected outcome

## Special AAA Cases (Acceptable Deviations)
These patterns may appear to deviate but are considered valid:

1. **No Arrange for Static/Constructor**: When testing static methods or constructors, arrange section may be absent
2. **Shared Before/After**: Arrange in @Before or Assert in @After methods
3. **Expected Exception**: @Test(expected=Exception.class) serves as implicit assertion
4. **Implicit Act**: Assertion implicitly executes action (e.g., equals() method testing)

## AAA Issues to Detect

### Deviation Patterns (Structure Issues):
1. **Multiple AAA**: Test contains multiple <arrange,act,assert> sequences
   - Violates single responsibility principle
   - Each test should focus on one scenario
   
2. **Missing Assert**: <arrange,act> without assertion
   - No verification of expected behavior
   - Test provides no explicit validation

3. **Assert Pre-condition**: <arrange,assert,act,assert>
   - Asserts preconditions before actual action
   - Should use Assume.assumeXXX() instead

### Design Issues (Quality Problems):
4. **Obscure Assert**: Complex assertion logic (cyclomatic complexity > 2)
   - Contains if/else, loops, try-catch in assertions
   - Consider Hamcrest matchers for cleaner assertions

5. **Arrange & Quit**: <arrange,if(condition)return,act,assert>
   - Silent return if preconditions not met
   - Should use Assume API to skip tests properly

6. **Multiple Acts**: <arrange,act1,act2,...,actn,assert>
   - Sequential dependent actions before assertion
   - Only final action's result is verified
   - Consider splitting into separate test cases

7. **Suppressed Exception**: <arrange,try{act}catch{suppress},assert>
   - Catches and hides exceptions from action
   - Failures may go unnoticed
   - Should throw exceptions to expose failures

## Analysis Guidelines
1. Most test cases should be "Good AAA" with no issues
2. Each test case can have at most 2 types of AAA issues
3. Focus on the test's target method (focal method)
4. Consider method names - they often indicate test intentions
5. Check for proper exception handling and assertion completeness

## Input Format
<test_code>Unit test code</test_code>
<ast>Abstract syntax tree sequence</ast>
<production_code>Production code being tested</production_code>
<imported_lib>Imported libraries</imported_lib>
<before>@Before method implementation</before>
<after>@After method implementation</after>

## Output Format
<analysis>
  <focal_method>The main method being tested</focal_method>
  <issueType>Good AAA | [Issue Type 1] | [Issue Type 1, Issue Type 2]</issueType>
  <sequence>Actual sequence pattern found</sequence>
  <reasoning>
    Detailed explanation including:
    - How the pattern deviates from correct AAA
    - Specific code elements causing the issue
    - Impact on test reliability/maintainability
    - Suggested improvements
  </reasoning>
</analysis>

Remember: Prioritize identifying the focal method being tested and assess whether the test effectively validates its behavior following AAA best practices."""
    
    def __init__(self, api_key: str, model: str = "o4-mini"):
        """
        Initialize analyzer
        
        Args:
            api_key: OpenAI API key
            model: Model name to use
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.cost_calculator = CostCalculator()
    
    def analyze(self, formatted_test_case: str, reasoning_effort: str = "medium") -> str:
        """
        Analyze AAA pattern of test case
        
        Args:
            formatted_test_case: Formatted test case
            reasoning_effort: Reasoning effort level
            
        Returns:
            Analysis result
        """
        
        try:
            # Prepare the basic request parameters
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": formatted_test_case}
                ],
                "response_format": {"type": "text"}
            }
            
            # Only add reasoning_effort for models that support it (o1 series)
            if self._model_supports_reasoning_effort():
                request_params["reasoning_effort"] = reasoning_effort
            
            response = self.client.chat.completions.create(**request_params)
            
            # Extract and track token usage
            usage = self.cost_calculator.extract_token_usage(response)
            cost = self.cost_calculator.calculate_cost(usage, self.model)
            self.cost_calculator.add_usage(usage, cost)
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def analyze_with_cost(self, formatted_test_case: str, reasoning_effort: str = "medium") -> Tuple[str, TokenUsage, CostInfo]:
        """
        Analyze AAA pattern of test case and return cost information
        
        Args:
            formatted_test_case: Formatted test case
            reasoning_effort: Reasoning effort level
            
        Returns:
            Tuple of (analysis_result, token_usage, cost_info)
        """
        
        try:
            # Prepare the basic request parameters
            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": formatted_test_case}
                ],
                "response_format": {"type": "text"}
            }
            
            # Only add reasoning_effort for models that support it (o1 series)
            if self._model_supports_reasoning_effort():
                request_params["reasoning_effort"] = reasoning_effort
            
            response = self.client.chat.completions.create(**request_params)
            
            # Extract token usage and cost information
            usage = self.cost_calculator.extract_token_usage(response)
            cost = self.cost_calculator.calculate_cost(usage, self.model)
            self.cost_calculator.add_usage(usage, cost)
            
            return response.choices[0].message.content, usage, cost
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def _model_supports_reasoning_effort(self) -> bool:
        """Check if the model supports reasoning_effort parameter"""
        model_lower = self.model.lower()
        return any(pattern in model_lower for pattern in ["o1", "o4", "o3"])
    
    def get_cost_summary(self, verbose: bool = False) -> str:
        """
        Get formatted cost summary
        
        Args:
            verbose: Whether to show detailed breakdown
            
        Returns:
            Formatted cost summary string
        """
        return self.cost_calculator.format_cost_summary(verbose)
    
    def get_cost_data(self) -> dict:
        """
        Get raw cost and usage data
        
        Returns:
            Dictionary with cost and usage information
        """
        return self.cost_calculator.get_summary() 