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
   Example:
   ```java
   @Test
   public void testStaticMethod() {
       int result = MathUtils.add(5, 3);  // Act
       assertEquals(8, result);           // Assert
   }
   ```
2. **Shared Before/After**: Arrange in @Before or Assert in @After methods
   Example:
   ``java
   @Before
   public void setup() {
       database = new Database();  // Arrange in @Before
   }
   
   @Test
   public void testQuery() {
       Result result = database.query("SELECT *");  // Act
       assertNotNull(result);                       // Assert
   }
   ```
3. **Expected Exception**: @Test(expected=Exception.class) serves as implicit assertion
   Example:
   ```java
   @Test(expected = IllegalArgumentException.class)
   public void testInvalidInput() {
       calculator.divide(10, 0);  // Act (Assert is implicit via annotation)
   }
   ```
4. **Implicit Act**: Assertion implicitly executes action (e.g., equals() method testing)
   Example:
   ```java
   @Test
   public void testEquals() {
       Person p1 = new Person("John");     // Arrange
       Person p2 = new Person("John");     // Arrange
       assertEquals(p1, p2);               // Assert (implicitly calls p1.equals(p2))
   }
   ```

## AAA Issues to Detect

### Deviation Patterns (Structure Issues):
1. **Multiple AAA**: Test contains multiple <arrange,act,assert> sequences
   - Violates single responsibility principle
   - Each test should focus on one scenario
    Example:
    ```java
    @Test
    public void testMultipleScenarios() {
        // First AAA sequence
        Calculator calc = new Calculator();    // Arrange 1
        int sum = calc.add(5, 3);             // Act 1
        assertEquals(8, sum);                  // Assert 1
        
        // Second AAA sequence - VIOLATION
        calc.clear();                          // Arrange 2
        int product = calc.multiply(4, 2);     // Act 2
        assertEquals(8, product);              // Assert 2
    }
    ```
    Issue: Violates single responsibility principle. Should be split into testAdd() and testMultiply().
   
2. **Missing Assert**: <arrange,act> without assertion
   - No verification of expected behavior
   - Test provides no explicit validation
   Example:
    ```java
    @Test
    public void testSaveUser() {
        User user = new User("John");          // Arrange
        userRepository.save(user);             // Act
        // No assertion - VIOLATION
    }
    ```
    Issue: No verification of expected behavior. Add assertions like `assertTrue(userRepository.contains(user))`.

3. **Assert Pre-condition**: <arrange,assert,act,assert>
   - Asserts preconditions before actual action
   - Should use Assume.assumeXXX() instead
   Example:
    ```java
    @Test
    public void testUpdateUser() {
        User user = userRepository.findById(1);     // Arrange
        assertNotNull(user);                        // Assert precondition - VIOLATION
        assertEquals("John", user.getName());       // Assert precondition - VIOLATION
        
        user.setName("Jane");                       // Act
        userRepository.save(user);                  // Act
        
        assertEquals("Jane", user.getName());       // Assert
    }
    ```
    Issue: Use `Assume.assumeNotNull(user)` instead of assertions for preconditions.

### Design Issues (Quality Problems):
4. **Obscure Assert**: Complex assertion logic (cyclomatic complexity > 2)
   - Contains if/else, loops, try-catch in assertions
   - Consider Hamcrest matchers for cleaner assertions
   Example:
    ```java
    @Test
    public void testProcessData() {
        DataProcessor processor = new DataProcessor();
        List<Result> results = processor.process(data);    // Act
        
        // Obscure assertion with complex logic - VIOLATION
        boolean found = false;
        for (Result r : results) {
            if (r.getType().equals("SUCCESS")) {
                if (r.getValue() > 100) {
                    found = true;
                    break;
                }
            }
        }
        assertTrue(found);
    }
    ```
    Issue: Use Hamcrest matchers: `assertThat(results, hasItem(allOf(hasProperty("type", "SUCCESS"), hasProperty("value", greaterThan(100)))))`.

5. **Arrange & Quit**: <arrange,if(condition)return,act,assert>
   - Silent return if preconditions not met
   - Should use Assume API to skip tests properly
   Example:
    ```java
    @Test
    public void testDatabaseOperation() {
        Connection conn = getConnection();          // Arrange
        if (conn == null) {
            return;  // VIOLATION - Silent quit
        }
        
        Result result = conn.executeQuery("...");   // Act
        assertNotNull(result);                      // Assert
    }
    ```
    Issue: Use `Assume.assumeNotNull(conn)` to properly skip test when preconditions aren't met.

6. **Multiple Acts**: <arrange,act1,act2,...,actn,assert>
   - Sequential dependent actions before assertion
   - Only final action's result is verified
   - Consider splitting into separate test cases
   IMPORTANT: This is VERY RARE. Only identify as Multiple Acts when:
        - Test name explicitly indicates testing multiple operations (e.g., testCreateAndUpdate, testLoginAndLogout)
        - Each action depends on the previous action's result
        - Only the final result is asserted

    Valid Multiple Acts Example:
    ```java
    @Test
    public void testCreateAndRetrieve() {  // Name indicates testing TWO operations
        UserService service = new UserService();
        
        // First action
        Long userId = service.createUser("John");    // Act 1: Create
        
        // Second action that depends on first
        User user = service.getUser(userId);         // Act 2: Retrieve using result from Act 1
        
        // Only asserts final result
        assertEquals("John", user.getName());        // Assert only the retrieve operation
    }
    ```

    NOT Multiple Acts (just arrangement):
    ```java
    @Test
    public void testGetUser() {  // Name indicates testing ONE operation
        UserService service = new UserService();
        
        // These are arrangements, not acts
        Long userId = service.createUser("John");    // Arrange - setup data
        cache.clear();                               // Arrange - setup state
        
        // The actual act being tested
        User user = service.getUser(userId);         // Act - the focal method
        
        assertEquals("John", user.getName());        // Assert
    }
    ```
    Key Distinction: Without explicit naming intent (like testAandB), treat earlier method calls as arrangement for the focal method being tested.
   
7. **Suppressed Exception**: <arrange,try{act}catch{suppress},assert>
   - Catches and hides exceptions from action
   - Failures may go unnoticed
   - Should throw exceptions to expose failures
   Example:
    ```java
    @Test
    public void testFileOperation() {
        FileHandler handler = new FileHandler();
        
        try {
            handler.readFile("test.txt");    // Act
        } catch (IOException e) {
            // Suppressing exception - VIOLATION
            e.printStackTrace();
        }
        
        assertTrue(handler.isReady());       // Assert
    }
    ```
    Issue: Exceptions should propagate. Add `throws IOException` to test method or use `assertThrows()`.

## Analysis Guidelines
1. Most test cases should be "Good AAA" with no issues
2. Each test case can have at most 2 types of AAA issues
3. Focus on the test's target method (focal method)
4. Consider method names - they often indicate test intentions
5. Check for proper exception handling and assertion completeness

###Critical Analysis Guidelines for Multiple Acts

1. Identify the Focal Method First: Determine what method/functionality the test is actually testing
2. Check Test Name: Test names often reveal intentions (especially for Multiple Acts)
3. Multiple Acts is RARE:
    - Only when test name shows intent to test multiple operations (testAandB, testCreateAndUpdate)
    - Otherwise, earlier method calls are just arrangement for the final focal method

4. Examine Control Flow: Look for conditional logic, loops, and exception handling
5. Verify Assertion Coverage: Ensure all important outcomes are verified

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