"""Main Gradio application entry point."""

import os
import uuid
from datetime import datetime
from typing import Optional, Tuple, List
import gradio as gr
from dotenv import load_dotenv

# Import our modules
from src import database, chat_service, prompt_loader


# Global state for app initialization
app_initialized = False
initialization_error: Optional[str] = None


def startup_checks() -> Tuple[bool, Optional[str]]:
    """
    Run all startup checks and return success status and error message if any.

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # 1. Load environment variables
    load_dotenv()

    # 2. Verify all required environment variables
    required_env_vars = [
        "ANTHROPIC_API_KEY",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"

    # 3. Test database connection
    try:
        if not database.test_connection():
            return False, "Unable to connect to database. Please check configuration."
    except Exception as e:
        return False, f"Database connection error: {str(e)}"

    # 4. Validate Anthropic API key
    try:
        if not chat_service.validate_api_key():
            return False, "Unable to connect to Claude API. Please check API key."
    except Exception as e:
        return False, f"Claude API error: {str(e)}"

    # 5. Verify system prompt template exists
    if not prompt_loader.validate_template_exists():
        return False, "System prompt template not found at prompts/chat_system.mustache"

    return True, None


def initialize_app():
    """Initialize the application and run startup checks."""
    global app_initialized, initialization_error

    print("Running startup checks...")
    success, error = startup_checks()

    if success:
        app_initialized = True
        initialization_error = None
        print("All startup checks passed. Application ready.")
    else:
        app_initialized = False
        initialization_error = error
        print(f"Startup check failed: {error}")


def load_document_on_startup(request: gr.Request) -> Tuple[str, str, str, bool, str, str]:
    """
    Load document based on URL parameter on page load.

    Args:
        request: Gradio request object containing URL parameters

    Returns:
        Tuple of (error_message, q_value, session_uuid, chat_enabled, resume, jd)
    """
    # Check if app initialized successfully
    if not app_initialized:
        error_msg = f"**Error:** {initialization_error}"
        return error_msg, "", str(uuid.uuid4()), False, "", ""

    # Extract 'q' parameter from URL
    q_param = request.query_params.get("q", "").strip()

    if not q_param:
        error_msg = "**Error:** 'q' parameter must be specified in the URL"
        return error_msg, "", str(uuid.uuid4()), False, "", ""

    # Generate session UUID
    session_uuid = str(uuid.uuid4())

    # Try to retrieve document from database
    try:
        result = database.get_document_by_name(q_param)

        if result is None:
            error_msg = f"**Error:** No document found with name '{q_param}'"
            return error_msg, q_param, session_uuid, False, "", ""

        resume, jd = result

        # Success - return empty error, enable chat, and populate fields
        return "", q_param, session_uuid, True, resume or "", jd or ""

    except Exception as e:
        error_msg = f"**Error:** Database error while retrieving document: {str(e)}"
        return error_msg, q_param, session_uuid, False, "", ""


def chat_function(
    message: str,
    history: List[List[str]],
    session_uuid: str,
    resume: str,
    jd: str
) -> Tuple[List[List[str]], str]:
    """
    Process chat message with streaming.

    Args:
        message: User's message
        history: Chat history in Gradio format [[user_msg, bot_msg], ...]
        session_uuid: Current session UUID
        resume: Resume content
        jd: Job description content

    Returns:
        Tuple of (updated_history, empty_string_to_clear_input)
    """
    if not message.strip():
        return history, ""

    # Save user message to database
    timestamp = datetime.now()
    database.save_message(session_uuid, "user", message, timestamp)

    # Retrieve session history from database
    db_messages = database.get_session_history(session_uuid)

    # Convert to Anthropic API format
    api_messages = chat_service.format_message_history(db_messages or [])

    # Load and render system prompt
    system_prompt = prompt_loader.get_system_prompt(resume, jd)

    if system_prompt is None:
        # Fallback if template loading fails
        system_prompt = prompt_loader.render_prompt("", resume, jd)

    # Add current user message to history display
    history = history + [[message, None]]
    yield history, ""

    # Stream response from Claude
    full_response = ""
    stream_generator = chat_service.stream_message(api_messages, system_prompt)

    for chunk in stream_generator:
        full_response += chunk
        # Update the last message in history with accumulated response
        history[-1][1] = full_response
        yield history, ""

    # Save assistant response to database
    database.save_message(session_uuid, "assistant", full_response, datetime.now())

    return history, ""


def create_interface():
    """Create and configure the Gradio interface."""
    initialize_app()

    with gr.Blocks(title="Career Advisor Chat") as demo:
        # State components
        q_state = gr.State("")
        session_uuid_state = gr.State("")

        # Row 1: Error message area
        error_display = gr.Markdown(visible=False, elem_classes=["error-message"])

        # Row 2: Chat interface
        chatbot = gr.Chatbot(
            label="Chat with Career Advisor",
            height=500,
        )

        # Row 3: Message input
        with gr.Row():
            message_input = gr.Textbox(
                label="Your message",
                placeholder="Type your message here...",
                scale=9,
                lines=2,
            )
            send_button = gr.Button("Send", scale=1, variant="primary")

        # Row 4: Two columns for resume and job description
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Accordion("Resume", open=True, visible=False) as resume_accordion:
                    resume_display = gr.Markdown(
                        value="",
                        elem_classes=["document-display"],
                    )
            with gr.Column(scale=1):
                with gr.Accordion("Job Description", open=True, visible=False) as jd_accordion:
                    jd_display = gr.Markdown(
                        value="",
                        elem_classes=["document-display"],
                    )

        # Load document on page load
        def on_load(request: gr.Request):
            error_msg, q_val, sess_uuid, chat_enabled, resume, jd = load_document_on_startup(request)

            # Determine visibility
            error_visible = len(error_msg) > 0
            resume_visible = len(resume) > 0
            jd_visible = len(jd) > 0

            return (
                gr.update(value=error_msg, visible=error_visible),  # error_display
                q_val,  # q_state
                sess_uuid,  # session_uuid_state
                gr.update(interactive=chat_enabled),  # message_input
                gr.update(interactive=chat_enabled),  # send_button
                gr.update(visible=resume_visible),  # resume_accordion
                gr.update(value=resume),  # resume_display
                gr.update(visible=jd_visible),  # jd_accordion
                gr.update(value=jd),  # jd_display
            )

        demo.load(
            fn=on_load,
            inputs=None,
            outputs=[
                error_display,
                q_state,
                session_uuid_state,
                message_input,
                send_button,
                resume_accordion,
                resume_display,
                jd_accordion,
                jd_display,
            ],
        )

        # Handle message sending
        send_button.click(
            fn=chat_function,
            inputs=[message_input, chatbot, session_uuid_state, resume_display, jd_display],
            outputs=[chatbot, message_input],
        )

        message_input.submit(
            fn=chat_function,
            inputs=[message_input, chatbot, session_uuid_state, resume_display, jd_display],
            outputs=[chatbot, message_input],
        )

    return demo


def main():
    """Main entry point for the application."""
    # Get port from environment or use default
    port = int(os.getenv("APP_PORT", 7860))

    # Create and launch the Gradio interface
    demo = create_interface()

    print(f"Starting Gradio application on port {port}...")

    demo.launch(
        server_port=port,
        server_name="0.0.0.0",  # Allow external access
        share=False,
    )


if __name__ == "__main__":
    main()
