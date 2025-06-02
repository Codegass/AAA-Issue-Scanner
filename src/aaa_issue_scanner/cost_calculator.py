"""
Cost Calculator for AAA Issue Scanner

Calculates token usage and associated costs for OpenAI API calls.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from openai.types.chat import ChatCompletion


@dataclass
class TokenUsage:
    """Token usage information for a single API call"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0  # For cached input tokens

    @property
    def input_tokens(self) -> int:
        """Non-cached input tokens"""
        return self.prompt_tokens - self.cached_tokens


@dataclass
class CostInfo:
    """Cost information for a single API call"""
    input_cost: float
    cached_input_cost: float
    output_cost: float
    total_cost: float
    
    def __add__(self, other: 'CostInfo') -> 'CostInfo':
        """Add two CostInfo objects"""
        return CostInfo(
            input_cost=self.input_cost + other.input_cost,
            cached_input_cost=self.cached_input_cost + other.cached_input_cost,
            output_cost=self.output_cost + other.output_cost,
            total_cost=self.total_cost + other.total_cost
        )


class CostCalculator:
    """Calculates token usage and costs for OpenAI API calls"""
    
    # Pricing information per million tokens (USD)
    MODEL_PRICING = {
        "o4-mini": {
            "input": 1.10,
            "cached_input": 0.275,
            "output": 4.40
        },
        "gpt-4.1": {
            "input": 2.00,
            "cached_input": 0.50,
            "output": 8.00
        },
        "gpt-4.1-mini": {
            "input": 0.40,
            "cached_input": 0.10,
            "output": 1.60
        }
    }
    
    def __init__(self):
        """Initialize cost calculator"""
        self.total_usage = TokenUsage(0, 0, 0, 0)
        self.total_cost = CostInfo(0.0, 0.0, 0.0, 0.0)
        self.call_count = 0
    
    def extract_token_usage(self, response: ChatCompletion) -> TokenUsage:
        """
        Extract token usage from OpenAI API response
        
        Args:
            response: OpenAI API response
            
        Returns:
            TokenUsage object with token counts
        """
        usage = response.usage
        if not usage:
            return TokenUsage(0, 0, 0, 0)
        
        # Extract cached tokens if available (newer API versions)
        cached_tokens = 0
        if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
            cached_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', 0)
        
        return TokenUsage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cached_tokens=cached_tokens
        )
    
    def calculate_cost(self, usage: TokenUsage, model: str) -> CostInfo:
        """
        Calculate cost for given token usage and model
        
        Args:
            usage: Token usage information
            model: Model name
            
        Returns:
            CostInfo object with cost breakdown
        """
        
        # Normalize model name for pricing lookup
        model_key = self._normalize_model_name(model)
        
        if model_key not in self.MODEL_PRICING:
            # Default to o4-mini pricing for unknown models
            model_key = "o4-mini"
        
        pricing = self.MODEL_PRICING[model_key]
        
        # Calculate costs (pricing is per million tokens)
        input_cost = (usage.input_tokens * pricing["input"]) / 1_000_000
        cached_input_cost = (usage.cached_tokens * pricing["cached_input"]) / 1_000_000
        output_cost = (usage.completion_tokens * pricing["output"]) / 1_000_000
        
        total_cost = input_cost + cached_input_cost + output_cost
        
        return CostInfo(
            input_cost=input_cost,
            cached_input_cost=cached_input_cost,
            output_cost=output_cost,
            total_cost=total_cost
        )
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for pricing lookup"""
        model_lower = model.lower()
        
        # Map common model name variants
        if "o4-mini" in model_lower or "o1-mini" in model_lower:
            return "o4-mini"
        elif "gpt-4.1-mini" in model_lower or "gpt-4o-mini" in model_lower:
            return "gpt-4.1-mini"
        elif "gpt-4.1" in model_lower or "gpt-4o" in model_lower:
            return "gpt-4.1"
        
        # Default to o4-mini for unknown models
        return "o4-mini"
    
    def add_usage(self, usage: TokenUsage, cost: CostInfo):
        """
        Add usage and cost to running totals
        
        Args:
            usage: Token usage to add
            cost: Cost information to add
        """
        self.total_usage.prompt_tokens += usage.prompt_tokens
        self.total_usage.completion_tokens += usage.completion_tokens
        self.total_usage.total_tokens += usage.total_tokens
        self.total_usage.cached_tokens += usage.cached_tokens
        
        self.total_cost += cost
        self.call_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all token usage and costs
        
        Returns:
            Dictionary with usage and cost summary
        """
        avg_tokens_per_call = (
            self.total_usage.total_tokens / self.call_count 
            if self.call_count > 0 else 0
        )
        
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_usage.total_tokens,
            "prompt_tokens": self.total_usage.prompt_tokens,
            "completion_tokens": self.total_usage.completion_tokens,
            "cached_tokens": self.total_usage.cached_tokens,
            "avg_tokens_per_call": round(avg_tokens_per_call, 1),
            "total_cost": round(self.total_cost.total_cost, 6),
            "input_cost": round(self.total_cost.input_cost, 6),
            "cached_input_cost": round(self.total_cost.cached_input_cost, 6),
            "output_cost": round(self.total_cost.output_cost, 6),
            "cache_savings": round(
                (self.total_usage.cached_tokens * self.MODEL_PRICING["o4-mini"]["input"] / 1_000_000) - 
                self.total_cost.cached_input_cost, 6
            ) if self.total_usage.cached_tokens > 0 else 0
        }
    
    def format_cost_summary(self, verbose: bool = False) -> str:
        """
        Format cost summary for display
        
        Args:
            verbose: Whether to show detailed breakdown
            
        Returns:
            Formatted cost summary string
        """
        summary = self.get_summary()
        
        if verbose:
            result = f"""
💰 Cost Summary:
   Total API calls: {summary['total_calls']}
   Total tokens: {summary['total_tokens']:,}
   - Input tokens: {summary['prompt_tokens'] - summary['cached_tokens']:,}
   - Cached tokens: {summary['cached_tokens']:,}
   - Output tokens: {summary['completion_tokens']:,}
   
   Cost breakdown:
   - Input cost: ${summary['input_cost']:.6f}
   - Cached input cost: ${summary['cached_input_cost']:.6f}
   - Output cost: ${summary['output_cost']:.6f}
   - Total cost: ${summary['total_cost']:.6f}"""
            
            if summary['cache_savings'] > 0:
                result += f"\n   - Cache savings: ${summary['cache_savings']:.6f}"
                
        else:
            result = f"💰 Total cost: ${summary['total_cost']:.4f} ({summary['total_calls']} calls, {summary['total_tokens']:,} tokens)"
            
            if summary['cache_savings'] > 0:
                result += f" | 💾 Saved: ${summary['cache_savings']:.4f}"
        
        return result 