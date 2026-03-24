import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib3
from urllib.parse import urljoin
import io
import PyPDF2
from google import genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication # <-- New for attachments
import markdown # <-- New for formatting
from xhtml2pdf import pisa # <-- New for PDF generation

load_dotenv()

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
# Suppress insecure request warnings for NIC firewall bypass
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Target URLs and Files
CBSE_URL = "https://cbseacademic.nic.in/circulars.html"
NOTICEBOARD_URL = "https://www.cbse.gov.in/cbsenew/cbse.html"
STATE_FILE = "last_circular_state.json"
OUTPUT_DIR = "cbse_circulars"
PROPOSALS_DIR = "edxso_proposals"

# Set up Gemini AI
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# STAGE 1: WEB SCRAPING & EXTRACTION
# ==========================================
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

def fetch_html_with_backoff(url, max_retries=5):
    timeout_sec = 2
    for attempt in range(max_retries):
        try:
            print(f"--> [Attempt {attempt + 1}] Pinging CBSE server...")
            response = requests.get(url, headers=get_headers(), timeout=(5, 15), verify=False)
            response.raise_for_status() 
            response.encoding = 'utf-8' 
            print("--> Success! Page loaded.")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {timeout_sec} seconds...")
            time.sleep(timeout_sec)
            timeout_sec *= 2  
    return None

def extract_latest_circulars(html_content, processed_circulars):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    new_circulars = []
    
    if not tables:
        return new_circulars

    rows = tables[0].find_all('tr')[1:] 
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            subject_td = cols[2]
            link_tag = subject_td.find('a', href=True)
            
            if not link_tag:
                continue 
                
            link = link_tag['href']
            if '.pdf' not in link.lower():
                continue
            
            if not link.startswith('http'):
                link = f"https://cbseacademic.nic.in/{link}"
                
            circular_no = cols[0].text.strip()
            
            # Skip if empty or already processed
            if not circular_no or circular_no in processed_circulars:
                continue
                
            month = cols[1].text.strip()
            subject = subject_td.text.strip()
            
            new_circulars.append({
                "circular_no": circular_no,
                "month": month,
                "subject": subject,
                "link": link
            })
            
    return new_circulars

def extract_noticeboard_circulars(html_content, processed_circulars):
    """Scrapes loose PDF links from the main CBSE noticeboard."""
    soup = BeautifulSoup(html_content, 'html.parser')
    new_circulars = []
    
    # Grab every single link on the page
    links = soup.find_all('a', href=True)
    
    for link_tag in links:
        link = link_tag['href']
        
        # We only want PDFs
        if '.pdf' not in link.lower():
            continue
            
        # --- THE FIX: Let Python handle the complex relative URL routing ---
        link = urljoin(NOTICEBOARD_URL, link)
            
        # Since noticeboards don't have "Circular Numbers", we use the PDF filename
        file_id = link.split('/')[-1].replace('.pdf', '')
        circular_no = f"NB_{file_id}" # Prefix with NB_ so we know it came from the Noticeboard
        
        # Skip if already processed
        if not circular_no or circular_no in processed_circulars:
            continue
            
        # The subject is just the text of the link
        subject = link_tag.text.strip()
        if not subject:
            subject = "Urgent Noticeboard Update"
            
        new_circulars.append({
            "circular_no": circular_no,
            "month": "Noticeboard",
            "subject": subject,
            "link": link
        })
        
    return new_circulars

def extract_text_from_pdf(pdf_url):
    try:
        print(f"   -> Downloading PDF: {pdf_url}")
        response = requests.get(pdf_url, headers=get_headers(), verify=False, timeout=(5, 15))
        response.raise_for_status()
        
        pdf_file = io.BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        
        pdf_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pdf_text += extracted + "\n"
                
        return pdf_text.strip()
    except Exception as e:
        print(f"   -> Failed to read PDF: {e}")
        return None

# ==========================================
# STAGE 2: AI MAPPING LOGIC
# ==========================================
def generate_edxso_proposal(document_text, circular_link):
    master_prompt = f"""
You are an Expert Business Developer and Educational Consultant at EDXSO, an educational technology and institutional transformation company. 

Your objective is to analyze a newly released government compliance circular from the CBSE (Central Board of Secondary Education) and determine the strategic outreach approach.

### EDXSO'S 8 R-CUBE METHODOLOGY DOMAINS:
1. Governance & Leadership
2. School Environment & Learning Culture
3. Faculty Development
4. Curriculum Architecture
5. Student Engagement & Learning
6. Technology Integration
7. Parents, Alumni, and Community
8. Assessment Scope & Design

### EDXSO SERVICE PORTFOLIO (Only use if Pitching a Product):
1. IAOS (Institutional Acceleration Operating System)
2. R3 Framework
3. Competency-Based Assessment Engine
4. Gold Standard Competency Framework
5. Teacher Intelligence and Professional Development
6. Institutional Transformation Consulting
7. Digital Transformation & EdTech
8. Student Career Intelligence
9. Mental Health Intelligence

### STRATEGIC LOGIC INSTRUCTIONS:
1. Read the provided CBSE Circular Text carefully.
2. Evaluate its "Criticality" based on the R-Cube Domains. Is this a "Painkiller" or a "Vitamin"?
    - **PAINKILLER (High Criticality):** A strict mandate, severe compliance change, or major pedagogical shift directly impacting core R-Cube domains. (ACTION: Pitch an EDXSO Product/Service).
    - **VITAMIN (Low Criticality):** A generic notification, optional field trip (like a garden visit), competition, or general awareness campaign. (ACTION: DO NOT pitch a product. Provide a free "Value-Add Advisory" on how to align this with NEP 2020 to build goodwill).

### STRICT OUTPUT RULES (CRITICAL):
- DO NOT include any conversational preamble.
- DO NOT include headers like "To:", "From:", or "Date:".
- You must start your response immediately with the exact text "**Categorization:**".
- CRITICAL: You MUST leave a completely blank line between every single section and paragraph.

### EXACT PROPOSAL FORMAT TO FOLLOW:

**Categorization:** [State either "Painkiller (Critical Compliance - Product Pitch)" OR "Vitamin (Informational - Goodwill Advisory)"]

**Subject:** Lead Generation Strategy for [Insert concise Circular Subject]

**Source Document:** [Click here to view the original CBSE Circular]({circular_link})

**1. Circular Executive Summary:** [4-5 sentences summarizing the CBSE mandate]

**2. The School's Challenge/Opportunity:** [What schools need to do to comply (if Painkiller), OR how they can leverage this for enrichment (if Vitamin)]

**3. Outreach Strategy & Messaging:**

[IF YOU CLASSIFIED THIS AS A 'PAINKILLER', USE THIS BULLETED FORMAT:]
* **[Insert EDXSO Service Name]:** [4-5 sentences explaining exactly how it solves the severe compliance pain point]
* **[Insert next relevant EDXSO Service Name, if any]:** [4-5 sentences explaining exactly how it solves the pain point]

[IF YOU CLASSIFIED THIS AS A 'VITAMIN', USE THIS FORMAT INSTEAD AND DO NOT MENTION EDXSO PRODUCTS:]
* **NEP 2020 Value-Add Strategy:** [4-5 sentences advising the principal, for free, on how to drive actual learning outcomes from this circular, earn NEP compliance marks, or structure the activity properly to build institutional goodwill.]

**4. Proposed Email Closing Angle:** [A 2-3 sentence pitch or sign-off we should use when emailing these schools]

### CBSE CIRCULAR TEXT TO ANALYZE:
{document_text}
"""
    try:
        print("   -> AI evaluating circular criticality (Painkiller vs Vitamin)...")
        response = client.models.generate_content(
            model = "gemini-2.5-pro",
            contents = master_prompt
        )
        return response.text
    except Exception as e:
        print(f"   -> Gemini API Error: {e}")
        return None

# ==========================================
# STAGE 3: EMAIL DISPATCH
# ==========================================
def send_email_to_pm(circular_subject, proposal_text, circular_no):
    """Emails the generated EDXSO proposal and attaches a beautifully styled PDF."""
    
    # --- EMAIL CONFIGURATION ---
    SENDER_EMAIL = os.getenv("EMAIL_SENDER")
    APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD") 
    PM_EMAIL = os.getenv("EMAIL_RECEIVER") 
    
    # 1. Convert Gemini's Markdown to HTML
    html_body = markdown.markdown(proposal_text)
    
    # ---------------------------------------------------------
    # 2. THE EMAIL TEMPLATE (Clean, simple, screen-optimized)
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # 2. THE EMAIL TEMPLATE (Clean, simple, screen-optimized)
    # ---------------------------------------------------------
    email_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #2C3E50; padding: 20px; }}
        h1, h2, h3 {{ color: #2980B9; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        strong {{ color: #1A5276; }}
        p {{ margin-bottom: 16px; }} 
        ul {{ margin-bottom: 15px; padding-left: 20px; }}
        li {{ margin-bottom: 10px; }}
        /* --- NEW: Styling for the PM's Call to Action --- */
        .cta-box {{ 
            margin-top: 30px; 
            padding: 15px; 
            background-color: #e8f4f8; 
            border-left: 5px solid #2980B9; 
            font-size: 16px; 
            color: #004080;
            font-weight: bold;
        }}
    </style>
    </head>
    <body>
        {html_body}
        
        <div class="cta-box">
            CTA: Shall I make an EDXSO personalized proposal for the school?
        </div>
    </body>
    </html>
    """

    # ---------------------------------------------------------
    # 3. THE PDF TEMPLATE (Corporate letterhead, headers/footers)
    # ---------------------------------------------------------
    pdf_html = f"""
    <html>
    <head>
    <style>
        /* Define the physical page layout */
        @page {{
            size: A4;
            margin: 2cm;
            margin-top: 2.5cm;
            margin-bottom: 2.5cm;
            /* Repeated Header */
            @frame header_frame {{
                -pdf-frame-content: header_content;
                top: 1cm; margin-left: 2cm; margin-right: 2cm; height: 1cm;
            }}
            /* Repeated Footer */
            @frame footer_frame {{
                -pdf-frame-content: footer_content;
                bottom: 1cm; margin-left: 2cm; margin-right: 2cm; height: 1cm;
            }}
        }}
        
        /* Typography & Layout */
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #333333; }}
        h1, h2, h3 {{ color: #004080; border-bottom: 1.5px solid #004080; padding-bottom: 4px; margin-top: 24px; margin-bottom: 12px; }}
        strong {{ color: #002b5e; }}
        p {{ margin-bottom: 14px; text-align: justify; }} /* Justified text looks more formal in PDFs */
        ul {{ margin-bottom: 14px; padding-left: 25px; }}
        li {{ margin-bottom: 8px; }}
        
        /* Custom Elements */
        .header-text {{ text-align: right; border-bottom: 2px solid #004080; padding-bottom: 5px; color: #004080; font-size: 9pt; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
        .footer-text {{ text-align: center; font-size: 8pt; color: #777777; border-top: 1px solid #dddddd; padding-top: 5px; }}
        .title-box {{ background-color: #f4f8fb; padding: 15px; border-left: 5px solid #004080; margin-bottom: 25px; }}
    </style>
    </head>
    <body>
        <div id="header_content" class="header-text">
            EDXSO Internal Intelligence & Strategy Brief
        </div>
        
        <div id="footer_content" class="footer-text">
            EDXSO Confidential & Proprietary | Page <pdf:pagenumber> of <pdf:pagecount>
        </div>

        <div class="title-box">
            <h2 style="margin-top: 0; border: none; padding: 0; color: #004080;">CBSE Compliance & Lead Strategy</h2>
            <p style="margin: 0; font-size: 10pt; color: #555;"><strong>Document Ref:</strong> {circular_no}</p>
        </div>

        {html_body}
    </body>
    </html>
    """

    # --- EMAIL CONSTRUCTION ---
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = PM_EMAIL
    msg['Subject'] = f"New CBSE Compliance Lead: {circular_subject}"
    
    # Attach the simple HTML to the email body
    msg.attach(MIMEText(email_html, 'html'))
    
    # --- PDF GENERATION ---
    pdf_buffer = io.BytesIO()
    # Feed the advanced PDF HTML template into xhtml2pdf
    pisa.CreatePDF(pdf_html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    
    # Attach the newly formatted PDF
    safe_filename = circular_no.replace('/', '_').replace('\\', '_')
    pdf_attachment = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"EDXSO_Proposal_{safe_filename}.pdf")
    msg.attach(pdf_attachment)

    try:
        print(f"   -> Connecting to email server to send formatted proposal...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"   -> Formatted Email & Premium PDF successfully dispatched to PM!")
    except Exception as e:
        print(f"   -> Failed to send email: {e}")

# ==========================================
# PIPELINE ORCHESTRATION
# ==========================================
def run_pipeline():
    # Load checklist
    processed_circulars = []
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            processed_circulars = data.get("processed_circulars", [])

    print(f"Monitoring CBSE. Database currently holds {len(processed_circulars)} processed circulars.")
    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    
    all_new_circulars = []
    
    # --- Source 1: Academic Circulars ---
    print("\n[1/2] Checking Academic Circulars...")
    html_acad = fetch_html_with_backoff(CBSE_URL)
    if html_acad:
        acad_circulars = extract_latest_circulars(html_acad, processed_circulars)
        all_new_circulars.extend(acad_circulars)
        
    # --- Source 2: Main Noticeboard ---
    print("\n[2/2] Checking Main Noticeboard...")
    html_notice = fetch_html_with_backoff(NOTICEBOARD_URL)
    if html_notice:
        notice_circulars = extract_noticeboard_circulars(html_notice, processed_circulars)
        all_new_circulars.extend(notice_circulars)
        
    # --- Process Everything We Found ---
    if all_new_circulars:
        print(f"\nFound {len(all_new_circulars)} total unprocessed circular(s) across both boards!")
        print("-" * 50)
        
        for circular in all_new_circulars:
            print(f"\n[PROCESSING] {circular['circular_no']}")
            print(f"Subject: {circular['subject']}")
            
            # 1. Extract Data
            document_text = extract_text_from_pdf(circular['link'])
            
            if document_text:
                # 2. Save physical text file
                safe_filename = circular['circular_no'].replace('/', '_').replace('\\', '_') + ".txt"
                file_path = os.path.join(OUTPUT_DIR, safe_filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(document_text)
                print(f"   -> Saved raw text to {file_path}")
                
                # 3. Generate EDXSO Proposal via AI
                proposal = generate_edxso_proposal(document_text, circular['link'])
                if proposal:
                    print("\n" + "="*60)
                    print("EDXSO BUSINESS PROPOSAL GENERATED:")
                    print("="*60)
                    print(proposal)
                    print("="*60 + "\n")

                    proposal_filename = "Proposal_" + safe_filename
                    proposal_path = os.path.join(PROPOSALS_DIR, proposal_filename)
                    with open(proposal_path, "w", encoding="utf-8") as f:
                        f.write(proposal)
                    print(f"   -> Saved business proposal to {proposal_path}")

                    # --- NEW: Send it to the boss! ---
                    send_email_to_pm(circular['subject'], proposal, circular['circular_no'])
                
                # 4. Save state so we don't repeat this circular
                processed_circulars.append(circular['circular_no'])
                with open(STATE_FILE, 'w') as f:
                    json.dump({"processed_circulars": processed_circulars}, f)
            
            # 5. Courtesy pause for firewalls and API limits
            print("   -> Sleeping for 3 seconds...")
            time.sleep(3)
            
        print("\nPipeline execution complete! All caught up.")
                
    else:
        print("No new circulars found. Everything is up to date.")

if __name__ == "__main__":
    # Ensure you delete the old state file if you want to start fresh!
    run_pipeline()