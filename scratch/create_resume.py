from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def create_resume(path):
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "John Doe - Resume")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, "Email: john.doe@example.com")
    c.drawString(100, 715, "Skills: Python, JavaScript, React, SQL, AWS, Docker")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 690, "Experience")
    c.setFont("Helvetica", 12)
    c.drawString(100, 675, "Senior Developer at Tech Corp")
    c.drawString(100, 660, "- Developed scalable web applications using Python and React.")
    c.drawString(100, 645, "- Managed AWS infrastructure and Docker containers.")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 620, "Education")
    c.setFont("Helvetica", 12)
    c.drawString(100, 605, "BS in Computer Science, University of Technology")
    
    c.save()

if __name__ == "__main__":
    resume_path = os.path.join(os.getcwd(), "sample_resume.pdf")
    create_resume(resume_path)
    print(f"Sample resume created at: {resume_path}")
