"""Study guide functions"""
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from ai_helper import generate_study_guide
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch

study_guide_bp = Blueprint('study_guide', __name__)

@study_guide_bp.route('/generate-study-guide', methods=['POST'])
def handle_generate_study_guide():
    """Generate study guide endpoint"""
    data = request.json
    try:
        use_mock = os.environ.get('USE_MOCK_API', 'False').lower() == 'true'
        if use_mock:
            study_guide = mock_deekseek_api(data)
            success = True
            error = None
        else:
            study_guide, error = generate_study_guide(data)
            success = error is None

        if not success or not study_guide:
            return jsonify({"success": False, "error": error or "Failed to generate study guide"}), 500

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_filename = f"study_guide_{timestamp}.txt"
        pdf_filename = f"study_guide_{timestamp}.pdf"

        with open(os.path.join("static/guides", txt_filename), "w") as f:
            f.write(study_guide)

        class_name = data.get('class', 'General')
        unit = data.get('unit', 'Unknown')
        year = data.get('year', 'College')

        generate_pdf(
            study_guide,
            os.path.join("static/guides", pdf_filename),
            title=f"{class_name} - {unit}",
            education_level=year
        )

        return jsonify({"success": True, "filename": pdf_filename, "content": study_guide})

    except Exception as e:
        return jsonify({"success": False, "error": f"An unexpected error occurred: {str(e)}"}), 500

@study_guide_bp.route('/download/<filename>')
def download(filename):
    """Download endpoint"""
    file_path = os.path.join("static/guides", filename)
    if not os.path.exists(file_path) or ".." in filename:
        return "File not found", 404
    mime_type = "application/pdf" if filename.endswith(".pdf") else "text/plain"
    return send_file(file_path, mimetype=mime_type, as_attachment=True, download_name=filename)


def generate_pdf(text_content, output_path, title="Study Guide", education_level="College"):
    """Generate a PDF from the text content."""

    # Create the PDF document using ReportLab
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Define styles
    styles = getSampleStyleSheet()

    # Create custom styles without overwriting existing ones
    custom_title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#0077ff')
    )

    custom_subtitle_style = ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor('#505050')
    )

    custom_heading_style = ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=16,
        textColor=colors.HexColor('#0077ff')
    )

    custom_body_style = ParagraphStyle(
        name='CustomBodyText',
        parent=styles['BodyText'],
        fontSize=11,
        spaceBefore=6,
        spaceAfter=6
    )

    # Prepare the elements that will go into the PDF
    elements = []

    # Add title and subtitle
    title_text = f"STUDY GUIDE: {title.upper()}"
    elements.append(Paragraph(title_text, custom_title_style))

    date_text = f"Education Level: {education_level} | Generated on: {datetime.now().strftime('%Y-%m-%d')}"
    elements.append(Paragraph(date_text, custom_subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Process the text content by sections
    sections = text_content.split('=====')

    for section in sections:
        if not section.strip():
            continue

        # Try to split into section title and content
        parts = section.strip().split('\n', 1)

        if len(parts) > 1:
            section_title, section_content = parts
            elements.append(Paragraph(section_title.strip(), custom_heading_style))

            # Process each line of content
            for line in section_content.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Format bullet points and numbered lists
                if line.startswith('- '):
                    line = '• ' + line[2:]
                    line = '&nbsp;&nbsp;&nbsp;&nbsp;' + line
                elif line.startswith('   - '):
                    line = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;◦ ' + line[5:]

                elements.append(Paragraph(line, custom_body_style))
        else:
            # If only one part, treat it as regular content
            for line in section.strip().split('\n'):
                if line.strip():
                    elements.append(Paragraph(line.strip(), custom_body_style))

    # Add footer note
    elements.append(Spacer(1, 0.5 * inch))
    footer_text = "This study guide was automatically generated by TutorAI to help with your studies."
    elements.append(Paragraph(footer_text, custom_subtitle_style))

    # Build the PDF
    doc.build(elements)

    return output_path

def mock_deekseek_api(data):
    """Mock function to generate a study guide based on user input."""
    class_name = data.get('class', 'General')
    unit = data.get('unit', 'Unknown')
    year = data.get('year', 'College')
    details = data.get('details', '')

    study_guide = f"""
        ===== STUDY GUIDE FOR {class_name.upper()} - {unit.upper()} =====
        Year Level: {year}
        Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        ===== INTRODUCTION =====
        This study guide covers key concepts from {class_name}, focusing on the {unit} unit.
        {details if details else "No additional details provided."}

        ===== KEY CONCEPTS =====
        1. Main Concept One
        - Detail point
        - Detail point
        - Example application

        2. Main Concept Two
        - Detail point
        - Relationship to other concepts
        - Common misconceptions

        3. Main Concept Three
        - Detail point
        - Historical context
        - Modern applications

        ===== PRACTICE PROBLEMS =====
        1. Problem description
        Solution: Brief explanation

        2. Problem description
        Solution: Brief explanation

        ===== ADDITIONAL RESOURCES =====
        - Recommended textbook chapters
        - Online resources
        - Practice exercises

        ===== CONCLUSION =====
        This study guide was automatically generated to help with your studies.
        Feel free to supplement with your own notes and ask questions if anything is unclear.
    """

    return study_guide
