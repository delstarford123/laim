from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        # Logo placeholder (draws a green box)
        self.set_fill_color(27, 94, 32) # Dark Green
        self.rect(0, 0, 210, 20, 'F') # Top banner
        
        # Title text in the banner
        self.set_font('Arial', 'B', 15)
        self.set_text_color(255, 255, 255) # White text
        self.cell(0, 10, 'PROJECT CONCEPT NOTE', 0, 1, 'R')
        self.ln(10)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        # Page number and Date
        today = datetime.date.today().strftime("%B %d, %Y")
        self.cell(0, 10, f'Livestock AI Manager (LAIM) | Generated: {today} | Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(27, 94, 32) # Dark Green
        self.cell(0, 10, title.upper(), 0, 1, 'L')
        self.line(10, self.get_y(), 200, self.get_y()) # Green underline
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Times', '', 11)
        self.set_text_color(0, 0, 0)
        # encode/decode to clean up any hidden bad characters
        clean_body = body.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, clean_body)
        self.ln(5)

    def bullet_point(self, text):
        self.set_font('Times', '', 11)
        self.set_text_color(0, 0, 0)
        self.cell(10) # Indent
        # We use chr(149) which is the specific code for a bullet in PDF fonts
        self.cell(5, 6, chr(149), 0, 0) 
        clean_text = text.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, clean_text)

# --- CONTENT GENERATION ---

pdf = PDF()
pdf.alias_nb_pages()
pdf.add_page()

# 1. TITLE PAGE SECTION
pdf.ln(10)
pdf.set_font('Arial', 'B', 24)
pdf.set_text_color(46, 125, 50)
pdf.multi_cell(0, 10, 'LIVESTOCK AI MANAGER\n(LAIM)', 0, 'C')
pdf.ln(5)

pdf.set_font('Arial', 'I', 14)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(0, 8, 'A Data-Driven Decision Support System for Precision Artificial Insemination in Kenya', 0, 'C')
pdf.ln(20)

# 2. INTRODUCTION / BACKGROUND
pdf.chapter_title('1. Introduction & Background')
intro_text = (
    "Agriculture is the backbone of the Kenyan economy, contributing approximately 33% of the GDP. "
    "The dairy sector, specifically, is a critical source of livelihood for millions of smallholder farmers "
    "in regions such as Kakamega, Kiambu, and Uasin Gishu. However, the sector faces significant challenges "
    "in breeding efficiency. Many farmers rely on intuition rather than data when scheduling Artificial "
    "Insemination (AI), leading to low conception rates and high veterinary costs."
)
pdf.chapter_body(intro_text)

# 3. PROBLEM STATEMENT
pdf.chapter_title('2. Problem Statement')
problem_text = (
    "The current success rate of Artificial Insemination in smallholder farms often falls below 40%. "
    "Key contributing factors include:\n\n"
    "1. Inaccurate detection of the Estrus cycle (Heat).\n"
    "2. Poor matching of Sire (Bull) genetics to the specific Cow breed.\n"
    "3. Lack of historical record-keeping to track reproductive health.\n\n"
    "Failed inseminations result in wasted semen straws (approx. KES 1,500 - 4,000 per attempt), "
    "loss of milk production time, and extended calving intervals."
)
pdf.chapter_body(problem_text)

# 4. PROPOSED SOLUTION
pdf.chapter_title('3. The Innovation: LAIM')
solution_text = (
    "Livestock AI Manager (LAIM) is a web-based platform that leverages Machine Learning (XGBoost) "
    "to analyze biological metrics and predict the probability of conception success before the farmer pays for the service."
)
pdf.chapter_body(solution_text)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 8, 'Key Technical Features:', 0, 1)
pdf.bullet_point("Predictive Engine: Analyzes Age, Weight, BCS, and Activity Index to calculate a success percentage.")
pdf.bullet_point("Genetic Catalog: A digital database of Kenyan bulls (Friesian, Sahiwal, Boran) with fertility scores.")
pdf.bullet_point("Digital Records: Automated history logs for auditing past insemination attempts.")
pdf.bullet_point("Support System: Integrated ticketing system for farmer technical support.")
pdf.ln(5)

# 5. OBJECTIVES
pdf.chapter_title('4. Project Objectives')
pdf.bullet_point("To increase AI conception rates in pilot farms by at least 25%.")
pdf.bullet_point("To reduce the financial burden on farmers by preventing untimely inseminations.")
pdf.bullet_point("To digitize breeding records for better herd management and genetic tracking.")
pdf.bullet_point("To promote the use of data-driven agriculture in rural Kenya.")
pdf.ln(5)

# 6. TARGET AUDIENCE
pdf.chapter_title('5. Target Audience')
# FIX: Removed special "•" characters and used simple hyphens "-"
target_text = (
    "- Small to Medium-scale Dairy Farmers (1-50 cows).\n"
    "- Veterinary Officers and AI Technicians.\n"
    "- Agricultural Cooperatives and Dairy Societies."
)
pdf.chapter_body(target_text)

# 7. CONCLUSION
pdf.chapter_title('6. Conclusion')
conclusion_text = (
    "LAIM represents a significant step towards modernizing dairy farming in Kenya. "
    "By bridging the gap between biological data and actionable insights, the project aligns with "
    "the national goals of food security and economic empowerment for the agricultural workforce."
)
pdf.chapter_body(conclusion_text)

# --- SAVE FILE ---
output_filename = "LAIM_Project_Concept_Note.pdf"
pdf.output(output_filename)

print(f"✅ Successfully created: {output_filename}")