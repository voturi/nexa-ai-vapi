"""Skills engine for loading and managing skills."""
import os
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache

from app.core.config import settings


class SkillsEngine:
    """Engine for loading and managing skills from markdown files."""

    def __init__(self, base_path: str = None):
        """Initialize skills engine."""
        self.base_path = Path(base_path or settings.SKILLS_BASE_PATH)

    @lru_cache(maxsize=128)
    def load_skill(self, skill_path: str) -> str:
        """
        Load a single skill from markdown file.

        Args:
            skill_path: Relative path from base_path (e.g., 'verticals/tradies/CONVERSATION_STYLE.md')

        Returns:
            Content of the skill file
        """
        full_path = self.base_path / skill_path

        if not full_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def get_skills_for_vertical(self, vertical: str) -> List[str]:
        """
        Load all skills for a specific vertical.

        Args:
            vertical: Vertical name (e.g., 'tradies', 'hair_salon')

        Returns:
            List of skill contents
        """
        vertical_path = self.base_path / 'verticals' / vertical

        if not vertical_path.exists():
            return []

        skills = []
        for skill_file in vertical_path.glob('*.md'):
            with open(skill_file, 'r', encoding='utf-8') as f:
                skills.append(f.read())

        return skills

    def get_integration_skills(self, integrations: List[str]) -> List[str]:
        """
        Load skills for specific integrations.

        Args:
            integrations: List of integration names (e.g., ['google_calendar', 'hubspot'])

        Returns:
            List of skill contents
        """
        skills = []

        for integration in integrations:
            integration_path = self.base_path / 'integrations' / integration

            if integration_path.exists():
                for skill_file in integration_path.glob('*.md'):
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        skills.append(f.read())

        return skills

    def get_core_skills(self) -> List[str]:
        """
        Load all core skills (universal best practices).

        Returns:
            List of skill contents
        """
        core_path = self.base_path / 'core'

        if not core_path.exists():
            return []

        skills = []
        for skill_file in core_path.glob('*.md'):
            with open(skill_file, 'r', encoding='utf-8') as f:
                skills.append(f.read())

        return skills

    def build_system_prompt(
        self,
        vertical: str,
        integrations: List[str],
        tenant_config: Dict,
        dynamic_context: Optional[Dict] = None
    ) -> str:
        """
        Build complete system prompt with skills and context.

        Args:
            vertical: Tenant's vertical
            integrations: List of enabled integrations
            tenant_config: Tenant configuration dict
            dynamic_context: Real-time context (availability, caller history, etc.)

        Returns:
            Complete system prompt string
        """
        # Load skills
        vertical_skills = self.get_skills_for_vertical(vertical)
        integration_skills = self.get_integration_skills(integrations)
        core_skills = self.get_core_skills()

        # Build prompt
        prompt = f"""You are an AI voice receptionist for {tenant_config.get('business_name', 'the business')}.

<vertical>{vertical}</vertical>

<skills>
## Vertical-Specific Skills
{''.join(vertical_skills)}

## Integration Skills
{''.join(integration_skills)}

## Core Skills
{''.join(core_skills)}
</skills>

<tenant_config>
Business Name: {tenant_config.get('business_name')}
Phone: {tenant_config.get('phone')}
Timezone: {tenant_config.get('timezone')}
Operating Hours: {tenant_config.get('operating_hours', {})}
Services: {tenant_config.get('services', [])}
</tenant_config>
"""

        if dynamic_context:
            prompt += f"""
<dynamic_context>
{self._format_dynamic_context(dynamic_context)}
</dynamic_context>
"""

        return prompt

    def _format_dynamic_context(self, context: Dict) -> str:
        """Format dynamic context for prompt."""
        lines = []

        # Make the current date VERY clear for the AI
        if 'current_date' in context:
            lines.append(f"TODAY'S DATE: {context['current_date']}")

        if 'current_year' in context:
            lines.append(f"CURRENT YEAR: {context['current_year']}")

        if 'current_time' in context:
            lines.append(f"Current time: {context['current_time']}")

        if 'timezone' in context:
            lines.append(f"Timezone: {context['timezone']}")

        if 'availability' in context:
            lines.append(f"Available time slots: {context['availability']}")

        if 'caller_history' in context:
            lines.append(f"Caller history: {context['caller_history']}")

        return '\n'.join(lines)


# Singleton instance
skills_engine = SkillsEngine()
