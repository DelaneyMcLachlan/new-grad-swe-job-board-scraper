"""
Email module for sending job notifications
"""
import smtplib
import csv
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from collections import defaultdict
import config


class EmailSender:
    """Handle sending email notifications"""
    
    def __init__(self):
        self.host = config.EMAIL_HOST
        self.port = config.EMAIL_PORT
        self.user = config.EMAIL_USER
        self.password = config.EMAIL_PASSWORD
        self.to_email = config.EMAIL_TO
    
    def send_jobs_email(self, jobs, include_csv=True):
        """
        Send an email with new job listings in Excel-style format
        
        Args:
            jobs: List of Job objects to send
            include_csv: Whether to attach a CSV file
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not jobs:
            # Don't send empty email here - let send_no_jobs_email handle it
            return True
        
        if not all([self.user, self.password, self.to_email]):
            print("Email configuration incomplete. Please set EMAIL_USER, EMAIL_PASSWORD, and EMAIL_TO in .env file")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            today = datetime.now().strftime('%Y-%m-%d')
            msg['Subject'] = f"New Job Listings - {len(jobs)} Jobs Posted on {today}"
            msg['From'] = self.user
            msg['To'] = self.to_email
            
            # Create HTML email body (Excel-style table grouped by company)
            html_body = self._create_excel_style_html(jobs)
            text_body = self._create_text_body(jobs)
            
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach CSV file if requested
            if include_csv:
                csv_attachment = self._create_csv_attachment(jobs)
                if csv_attachment:
                    msg.attach(csv_attachment)
            
            # Send email
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            print(f"Successfully sent email with {len(jobs)} jobs to {self.to_email}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _create_excel_style_html(self, jobs):
        """Create Excel-style HTML table grouped by company"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Group jobs by company/source
        jobs_by_company = defaultdict(list)
        for job in jobs:
            company = job.source if hasattr(job, 'source') else 'Unknown'
            jobs_by_company[company].append(job)
        
        html = f"""
        <html>
          <head>
            <style>
              body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
              }}
              .header {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
              }}
              .company-section {{
                margin-bottom: 30px;
                background-color: white;
                border-radius: 5px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
              }}
              .company-header {{
                background-color: #34495e;
                color: white;
                padding: 15px;
                font-size: 18px;
                font-weight: bold;
              }}
              table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
              }}
              th {{
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 12px;
                text-align: left;
                border-bottom: 2px solid #bdc3c7;
                font-weight: bold;
                position: sticky;
                top: 0;
              }}
              td {{
                padding: 10px;
                border-bottom: 1px solid #ecf0f1;
                vertical-align: top;
              }}
              tr:hover {{
                background-color: #f8f9fa;
              }}
              .job-title {{
                font-weight: bold;
                color: #2980b9;
              }}
              .job-link {{
                color: #3498db;
                text-decoration: none;
              }}
              .job-link:hover {{
                text-decoration: underline;
              }}
              .description-cell {{
                max-width: 300px;
                overflow: hidden;
                text-overflow: ellipsis;
              }}
            </style>
          </head>
          <body>
            <div class="header">
              <h1>New Job Listings - {len(jobs)} Jobs Posted on {today}</h1>
              <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        # Create table for each company
        for company, company_jobs in sorted(jobs_by_company.items()):
            html += f"""
            <div class="company-section">
              <div class="company-header">
                {company.upper()} - {len(company_jobs)} Job(s)
              </div>
              <table>
                <thead>
                  <tr>
                    <th style="width: 25%;">Job Title</th>
                    <th style="width: 15%;">Location</th>
                    <th style="width: 10%;">Date Posted</th>
                    <th style="width: 10%;">Job ID</th>
                    <th style="width: 30%;">Description</th>
                    <th style="width: 10%;">Link</th>
                  </tr>
                </thead>
                <tbody>
            """
            
            for job in company_jobs:
                title = job.title if hasattr(job, 'title') else 'N/A'
                location = job.location if hasattr(job, 'location') else 'N/A'
                date_posted = job.date_posted.strftime('%Y-%m-%d') if (hasattr(job, 'date_posted') and job.date_posted) else 'N/A'
                job_id = job.job_id if hasattr(job, 'job_id') else 'N/A'
                description = (job.description[:200] + '...') if (hasattr(job, 'description') and job.description and len(job.description) > 200) else (job.description if (hasattr(job, 'description') and job.description) else 'N/A')
                url = job.url if (hasattr(job, 'url') and job.url) else '#'
                
                # Escape HTML characters
                title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                location = location.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                html += f"""
                  <tr>
                    <td class="job-title">{title}</td>
                    <td>{location}</td>
                    <td>{date_posted}</td>
                    <td>{job_id}</td>
                    <td class="description-cell">{description}</td>
                    <td>{f'<a href="{url}" class="job-link" target="_blank">View</a>' if url != '#' else 'N/A'}</td>
                  </tr>
                """
            
            html += """
                </tbody>
              </table>
            </div>
            """
        
        html += """
          </body>
        </html>
        """
        return html
    
    def _create_html_body(self, jobs):
        """Legacy method - redirects to Excel-style format"""
        return self._create_excel_style_html(jobs)
    
    def _create_text_body(self, jobs):
        """Create plain text email body grouped by company"""
        today = datetime.now().strftime('%Y-%m-%d')
        text = f"New Job Listings - {len(jobs)} Jobs Posted on {today}\n"
        text += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += "=" * 80 + "\n\n"
        
        # Group jobs by company
        jobs_by_company = defaultdict(list)
        for job in jobs:
            company = job.source if hasattr(job, 'source') else 'Unknown'
            jobs_by_company[company].append(job)
        
        for company, company_jobs in sorted(jobs_by_company.items()):
            text += f"\n{'=' * 80}\n"
            text += f"{company.upper()} - {len(company_jobs)} Job(s)\n"
            text += "=" * 80 + "\n\n"
            
            for job in company_jobs:
                text += f"Title: {job.title if hasattr(job, 'title') else 'N/A'}\n"
                text += f"Location: {job.location if (hasattr(job, 'location') and job.location) else 'N/A'}\n"
                text += f"Date Posted: {job.date_posted.strftime('%Y-%m-%d') if (hasattr(job, 'date_posted') and job.date_posted) else 'N/A'}\n"
                text += f"Job ID: {job.job_id if hasattr(job, 'job_id') else 'N/A'}\n"
                text += f"Description: {job.description[:300] if (hasattr(job, 'description') and job.description) else 'N/A'}\n"
                if hasattr(job, 'url') and job.url:
                    text += f"URL: {job.url}\n"
                text += "\n" + "-" * 80 + "\n\n"
        
        return text
    
    def _create_csv_attachment(self, jobs):
        """Create CSV attachment for Excel import"""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Company', 'Job Title', 'Location', 'Date Posted', 'Job ID', 'Description', 'URL'])
            
            # Write job data
            for job in jobs:
                company = job.source if hasattr(job, 'source') else 'Unknown'
                title = job.title if hasattr(job, 'title') else 'N/A'
                location = job.location if (hasattr(job, 'location') and job.location) else 'N/A'
                date_posted = job.date_posted.strftime('%Y-%m-%d') if (hasattr(job, 'date_posted') and job.date_posted) else 'N/A'
                job_id = job.job_id if hasattr(job, 'job_id') else 'N/A'
                description = job.description if (hasattr(job, 'description') and job.description) else 'N/A'
                url = job.url if (hasattr(job, 'url') and job.url) else 'N/A'
                
                writer.writerow([company, title, location, date_posted, job_id, description, url])
            
            # Create attachment
            csv_data = output.getvalue()
            output.close()
            
            attachment = MIMEBase('text', 'csv')
            attachment.set_payload(csv_data.encode('utf-8'))
            encoders.encode_base64(attachment)
            
            today = datetime.now().strftime('%Y-%m-%d')
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename=jobs_{today}.csv'
            )
            
            return attachment
            
        except Exception as e:
            print(f"Error creating CSV attachment: {e}")
            return None

