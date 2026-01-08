"""Mustache template loader for system prompts."""

import os
from typing import Optional
import pystache


# Cache for loaded template
_template_cache: Optional[str] = None


def validate_template_exists(template_path: str = "prompts/chat_system.mustache") -> bool:
    """
    Check template file exists on startup.

    Args:
        template_path: Path to the template file (relative to project root)

    Returns:
        bool: True if template exists, False otherwise
    """
    # Get the absolute path relative to the project root
    # The template path should be relative to where the app is run from
    if os.path.isabs(template_path):
        abs_path = template_path
    else:
        abs_path = os.path.abspath(template_path)

    exists = os.path.isfile(abs_path)

    if exists:
        print(f"Template file found: {abs_path}")
    else:
        print(f"Template file not found: {abs_path}")

    return exists


def load_template(template_path: str = "prompts/chat_system.mustache") -> Optional[str]:
    """
    Load and cache template file.

    Args:
        template_path: Path to the template file (relative to project root)

    Returns:
        str: Template content if successful, None otherwise
    """
    global _template_cache

    # Return cached template if already loaded
    if _template_cache is not None:
        return _template_cache

    try:
        # Get the absolute path
        if os.path.isabs(template_path):
            abs_path = template_path
        else:
            abs_path = os.path.abspath(template_path)

        # Read the template file
        with open(abs_path, 'r', encoding='utf-8') as f:
            _template_cache = f.read()

        print(f"Template loaded successfully from: {abs_path}")
        return _template_cache

    except FileNotFoundError:
        print(f"Template file not found: {template_path}")
        return None
    except Exception as e:
        print(f"Error loading template: {e}")
        return None


def render_prompt(template: str, resume: str, jd: str, email: Optional[str] = None) -> str:
    """
    Render template with resume, job description, and email context.

    Args:
        template: Mustache template string
        resume: Resume content
        jd: Job description content
        email: Applicant email address (defaults to APPLICANT_EMAIL env var)

    Returns:
        str: Rendered prompt with resume, jd, and email substituted
    """
    try:
        # Get email from environment if not provided
        if email is None:
            email = os.getenv("APPLICANT_EMAIL", "")

        # Create context dictionary for Mustache
        context = {
            "resume": resume,
            "jd": jd,
            "email": email
        }

        # Render the template using pystache
        rendered = pystache.render(template, context)

        return rendered

    except Exception as e:
        print(f"Error rendering template: {e}")
        # Return a basic fallback prompt if rendering fails
        return f"""You are a helpful career advisor assistant reviewing a resume against a job description.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Please provide thoughtful, specific feedback to help the hiring manager evaluate fit for this position."""


def get_system_prompt(resume: str, jd: str, template_path: str = "prompts/chat_system.mustache") -> Optional[str]:
    """
    Convenience function to load template and render prompt in one call.

    Args:
        resume: Resume content
        jd: Job description content
        template_path: Path to the template file (relative to project root)

    Returns:
        str: Rendered system prompt, or None if template loading fails
    """
    template = load_template(template_path)

    if template is None:
        return None

    return render_prompt(template, resume, jd)
