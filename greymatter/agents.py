#!/usr/bin/env python3
"""
Agents System - Specialized AI agents that spawn with fresh context

Each agent runs in isolation with its own context window,
preventing context pollution and enabling focused work.

Agents:
- PlanAgent: Design implementation plans
- ResearchAgent: Multi-step investigation
- DebugAgent: Systematic debugging
- ValidateAgent: RAG-judge + validation
- CodeAgent: Focused code implementation
- ReviewAgent: Code review
- ExplorerAgent: Codebase exploration
"""

import subprocess
import os
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class AgentResult:
    """Result from an agent run"""
    success: bool
    output: str
    artifacts: List[Dict] = None
    learnings: List[str] = None
    next_steps: List[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all agents"""

    name: str = "base"
    description: str = "Base agent"
    system_prompt: str = ""

    def __init__(self, ai_type: str = "claude", memory=None):
        self.ai_type = ai_type
        self.memory = memory

    @abstractmethod
    def build_prompt(self, task: str, context: Dict = None) -> str:
        """Build the prompt for this agent"""
        pass

    def run(self, task: str, context: Dict = None) -> AgentResult:
        """Run the agent with a task"""
        from .memory import get_memory

        memory = self.memory or get_memory()
        session_id = memory.start_session(f"{self.ai_type}-{self.name}", os.getcwd())

        prompt = self.build_prompt(task, context)

        # Inject relevant memory context
        mem_context = memory.build_context(query=task)
        if mem_context:
            prompt = f"{mem_context}\n\n---\n\n{prompt}"

        try:
            output = self._execute(prompt)

            # Extract learnings and save
            learnings = self._extract_learnings(output)
            for learning in learnings:
                memory.save(learning, type='agent-learning', source=self.name, importance=7)

            # Create handoff
            memory.create_handoff(
                session_id,
                summary=f"Agent {self.name} completed: {task[:100]}",
                next_steps='\n'.join(self._extract_next_steps(output)),
                artifacts=[{'type': 'output', 'content': output[:2000]}]
            )

            memory.end_session(session_id, 'completed')

            return AgentResult(
                success=True,
                output=output,
                learnings=learnings,
                next_steps=self._extract_next_steps(output)
            )

        except Exception as e:
            memory.end_session(session_id, 'error')
            return AgentResult(success=False, output="", error=str(e))

    def _execute(self, prompt: str) -> str:
        """Execute the AI with the prompt"""
        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            cmd = self._build_command(prompt_file)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            return result.stdout + result.stderr
        finally:
            os.unlink(prompt_file)

    def _build_command(self, prompt_file: str) -> List[str]:
        """Build command for the AI CLI"""
        if self.ai_type == 'claude':
            return ['claude', '--print', '-p', f'$(cat {prompt_file})']
        elif self.ai_type == 'gemini':
            return ['gemini', '-p', f'$(cat {prompt_file})']
        else:
            return ['ollama', 'run', 'llama3', f'$(cat {prompt_file})']

    def _extract_learnings(self, output: str) -> List[str]:
        """Extract learnings from output"""
        import re
        learnings = []
        patterns = [
            r"(?:Key )?[Ll]earning[s]?:\s*(.+?)(?:\n|$)",
            r"(?:Key )?[Ii]nsight[s]?:\s*(.+?)(?:\n|$)",
            r"[Dd]iscovered:\s*(.+?)(?:\n|$)",
            r"[Nn]ote[d]?:\s*(.+?)(?:\n|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output)
            learnings.extend(matches)
        return learnings[:10]  # Limit

    def _extract_next_steps(self, output: str) -> List[str]:
        """Extract next steps from output"""
        import re
        steps = []
        patterns = [
            r"[Nn]ext [Ss]tep[s]?:\s*(.+?)(?:\n|$)",
            r"[Tt]o[- ]?[Dd]o:\s*(.+?)(?:\n|$)",
            r"[Aa]ction [Ii]tem[s]?:\s*(.+?)(?:\n|$)",
            r"^\s*[-*]\s*(.+?)$",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output, re.MULTILINE)
            steps.extend(matches)
        return steps[:10]


class PlanAgent(BaseAgent):
    """Agent for designing implementation plans"""

    name = "plan"
    description = "Design and plan implementations"
    system_prompt = """You are a software architect. Your job is to:
1. Analyze the task requirements
2. Explore the codebase structure
3. Identify affected files and components
4. Design a step-by-step implementation plan
5. Consider edge cases and potential issues
6. Output a clear, actionable plan

Format your response as:
## Analysis
[Your analysis]

## Affected Files
[List of files]

## Implementation Plan
1. [Step 1]
2. [Step 2]
...

## Risks & Mitigations
[Potential issues and how to handle them]

## Next Steps
[Immediate actions to take]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Task\n{task}"
        if context:
            if context.get('files'):
                prompt += f"\n\n## Relevant Files\n{json.dumps(context['files'], indent=2)}"
            if context.get('constraints'):
                prompt += f"\n\n## Constraints\n{context['constraints']}"
        return prompt


class ResearchAgent(BaseAgent):
    """Agent for multi-step investigation"""

    name = "research"
    description = "Investigate and research topics"
    system_prompt = """You are a research specialist. Your job is to:
1. Break down the research question
2. Search for relevant information
3. Analyze findings
4. Synthesize conclusions
5. Provide actionable insights

Format your response as:
## Research Question
[Restated question]

## Findings
[Key findings with sources]

## Analysis
[Your analysis]

## Conclusions
[Main conclusions]

## Learnings
[Key takeaways to remember]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Research Topic\n{task}"
        if context and context.get('scope'):
            prompt += f"\n\n## Scope\n{context['scope']}"
        return prompt


class DebugAgent(BaseAgent):
    """Agent for systematic debugging"""

    name = "debug"
    description = "Systematic debugging and problem solving"
    system_prompt = """You are a debugging specialist. Your job is to:
1. Understand the error/issue
2. Identify potential causes
3. Create hypotheses
4. Design tests to verify hypotheses
5. Propose fixes

Format your response as:
## Issue Summary
[What's happening]

## Error Analysis
[Detailed analysis]

## Hypotheses
1. [Hypothesis 1]
2. [Hypothesis 2]

## Investigation Steps
[Steps to verify]

## Proposed Fix
[The fix]

## Learnings
[What we learned for future]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Issue\n{task}"
        if context:
            if context.get('error'):
                prompt += f"\n\n## Error Message\n```\n{context['error']}\n```"
            if context.get('stack_trace'):
                prompt += f"\n\n## Stack Trace\n```\n{context['stack_trace']}\n```"
            if context.get('code'):
                prompt += f"\n\n## Relevant Code\n```\n{context['code']}\n```"
        return prompt


class ValidateAgent(BaseAgent):
    """Agent for validation and verification"""

    name = "validate"
    description = "Validate implementations and verify correctness"
    system_prompt = """You are a validation specialist. Your job is to:
1. Review the implementation
2. Check against requirements
3. Identify potential issues
4. Verify edge cases
5. Provide validation verdict

Format your response as:
## Validation Summary
[Overall assessment]

## Requirements Check
- [x] Requirement 1: [status]
- [ ] Requirement 2: [status]

## Issues Found
[List of issues]

## Edge Cases
[Edge case analysis]

## Verdict
[PASS/FAIL with explanation]

## Recommendations
[Improvements if any]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Validation Task\n{task}"
        if context:
            if context.get('requirements'):
                prompt += f"\n\n## Requirements\n{context['requirements']}"
            if context.get('implementation'):
                prompt += f"\n\n## Implementation\n```\n{context['implementation']}\n```"
        return prompt


class CodeAgent(BaseAgent):
    """Agent for focused code implementation"""

    name = "code"
    description = "Implement code based on specifications"
    system_prompt = """You are a code implementation specialist. Your job is to:
1. Understand the specification
2. Write clean, correct code
3. Follow existing patterns in the codebase
4. Include appropriate error handling
5. Write tests if needed

Output only the code with minimal explanation.
Use proper formatting and comments.
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Implementation Task\n{task}"
        if context:
            if context.get('language'):
                prompt += f"\n\n## Language: {context['language']}"
            if context.get('examples'):
                prompt += f"\n\n## Examples\n{context['examples']}"
            if context.get('patterns'):
                prompt += f"\n\n## Patterns to Follow\n{context['patterns']}"
        return prompt


class ReviewAgent(BaseAgent):
    """Agent for code review"""

    name = "review"
    description = "Review code for quality and issues"
    system_prompt = """You are a code review specialist. Your job is to:
1. Review code for correctness
2. Check for security issues
3. Evaluate code quality
4. Suggest improvements
5. Verify best practices

Format your response as:
## Review Summary
[Overall assessment]

## Issues
### Critical
[Critical issues]

### Major
[Major issues]

### Minor
[Minor issues]

## Security
[Security assessment]

## Improvements
[Suggested improvements]

## Verdict
[APPROVE/REQUEST_CHANGES]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Review Request\n{task}"
        if context and context.get('code'):
            prompt += f"\n\n## Code\n```\n{context['code']}\n```"
        return prompt


class ExplorerAgent(BaseAgent):
    """Agent for codebase exploration"""

    name = "explorer"
    description = "Explore and understand codebases"
    system_prompt = """You are a codebase exploration specialist. Your job is to:
1. Map the codebase structure
2. Identify key components
3. Trace data flow
4. Document patterns
5. Create a mental model

Format your response as:
## Structure Overview
[High-level structure]

## Key Components
[Main components and their roles]

## Patterns Used
[Design patterns identified]

## Data Flow
[How data moves through the system]

## Entry Points
[Main entry points]

## Learnings
[Key insights about this codebase]
"""

    def build_prompt(self, task: str, context: Dict = None) -> str:
        prompt = f"{self.system_prompt}\n\n## Exploration Task\n{task}"
        if context and context.get('focus'):
            prompt += f"\n\n## Focus Area\n{context['focus']}"
        return prompt


# Agent registry
AGENTS = {
    'plan': PlanAgent,
    'research': ResearchAgent,
    'debug': DebugAgent,
    'validate': ValidateAgent,
    'code': CodeAgent,
    'review': ReviewAgent,
    'explorer': ExplorerAgent,
}


def get_agent(name: str, ai_type: str = 'claude') -> BaseAgent:
    """Get an agent by name"""
    if name not in AGENTS:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENTS.keys())}")
    return AGENTS[name](ai_type=ai_type)


def run_agent(name: str, task: str, ai_type: str = 'claude', context: Dict = None) -> AgentResult:
    """Convenience function to run an agent"""
    agent = get_agent(name, ai_type)
    return agent.run(task, context)
