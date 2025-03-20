"""Helper module for AI-powered study guide generation."""
import os
from flask import Blueprint
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ai_helper_blueprint = Blueprint("ai_helper", __name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-2baac3856127425998a967f88ff10c59")

def get_openai_client():
    """Creates OpenAI client with Deepseek params"""
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def generate_study_guide(data):
    """Generate a study guide using the DeepSeek API."""
    class_name = data.get('class', 'General')
    unit = data.get('unit', 'Unknown')
    year = data.get('year', 'College')
    details = data.get('details', '')

    system_prompt = (
        "You are a professional study guide creator. You create detailed, well-structured study guides for students. "
        "Thoughtfully consider a student's education level, course, and unit/topic to generate an in-depth, relevant study guide. "
        "Ensure that the study guide is appropriate for their education level. "
        "Format the study guide with the following sections, each preceded by '===== SECTION NAME =====' (including the equals signs and spaces):\n"
        "1. INTRODUCTION\n"
        "2. KEY CONCEPTS\n"
        "3. DEFINITIONS\n"
        "4. PRACTICE PROBLEMS\n"
        "5. ADDITIONAL RESOURCES\n"
        "6. CONCLUSION\n\n"
        "Use plain text formatting with clear section headers and bullet points."
        "Use bullet points with '- ' for main points and '   - ' for sub-points (with three spaces before the dash)."
        "Number lists as '1. ', '2. ', etc."
        "This exact formatting is critical as it will be used to generate a PDF document."
    )

    user_prompt = (
        f"I am a student at the {year} level studying {class_name}. "
        f"I need a study guide for the {unit} unit or topic. "
        f"Additional details: {details}\n\n"
        f"Please generate a comprehensive study guide to help me prepare for my exam or assignment."
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
            stream=False
        )

        content = response.choices[0].message.content

        if not content.strip().startswith("====="):
            formatted_content = f"""
            ===== STUDY GUIDE FOR {class_name.upper()} - {unit.upper()} =====

            {content}
            """
        else:
            formatted_content = content

        return formatted_content, None

    except Exception as error:
        error_msg = f"Error generating study guide: {str(error)}"
        print(error_msg)  # For debugging
        return None, error_msg
