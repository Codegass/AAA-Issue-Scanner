"""
Test Case Data Formatter

Converts JSON format test data to the format required by LLM.
"""

from typing import Dict, Any, List


class TestCaseFormatter:
    """Class responsible for formatting test case data to specified format"""
    
    def format_test_case(self, test_data: Dict[str, Any]) -> str:
        """
        Format test case data to LLM input format
        
        Args:
            test_data: Dictionary containing test case information
            
        Returns:
            Formatted string
        """
        
        # Extract each section
        test_code = test_data.get('testCaseSourceCode', '')
        ast_sequence = self._format_ast_sequence(test_data.get('parsedStatementsSequence', []))
        production_code = self._format_production_code(test_data.get('productionFunctionImplementations', []))
        imported_libs = self._format_imported_libs(test_data.get('importedPackages', []))
        before_method = self._format_before_methods(test_data)
        after_method = self._format_after_methods(test_data)
        
        # Assemble according to specified format
        formatted = f"""<test_code>{test_code}</test_code>
<ast>{ast_sequence}</ast>
<production_code>{production_code}</production_code>
<imported_lib>{imported_libs}</imported_lib>
<before>{before_method}</before>
<after>{after_method}</after>"""
        
        return formatted
    
    def _format_ast_sequence(self, statements: List[str]) -> str:
        """Format abstract syntax tree sequence"""
        if not statements:
            return ""
        return "\n".join(statements)
    
    def _format_production_code(self, implementations: List[str]) -> str:
        """Format production code implementations"""
        if not implementations:
            return ""
        return "\n\n".join(implementations)
    
    def _format_imported_libs(self, packages: List[str]) -> str:
        """Format imported libraries"""
        if not packages:
            return ""
        return "\n".join(packages)
    
    def _format_before_methods(self, test_data: Dict[str, Any]) -> str:
        """Format before methods (@Before, @BeforeEach, @BeforeAll)"""
        before_content = []
        
        # Extract different types of before methods
        before_methods = test_data.get('beforeMethods', [])
        before_all_methods = test_data.get('beforeAllMethods', [])
        
        # Add @BeforeAll methods first
        if before_all_methods:
            before_content.extend(before_all_methods)
        
        # Add @Before/@BeforeEach methods
        if before_methods:
            before_content.extend(before_methods)
        
        return "\n\n".join(before_content) if before_content else ""
    
    def _format_after_methods(self, test_data: Dict[str, Any]) -> str:
        """Format after methods (@After, @AfterEach, @AfterAll)"""
        after_content = []
        
        # Extract different types of after methods
        after_methods = test_data.get('afterMethods', [])
        after_all_methods = test_data.get('afterAllMethods', [])
        
        # Add @After/@AfterEach methods first
        if after_methods:
            after_content.extend(after_methods)
        
        # Add @AfterAll methods last
        if after_all_methods:
            after_content.extend(after_all_methods)
        
        return "\n\n".join(after_content) if after_content else "" 