"""
Database module for storing and managing job listings
"""
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()


class Job(Base):
    """Job model for database storage"""
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    location = Column(String(500))
    description = Column(Text)
    date_posted = Column(DateTime)
    source = Column(String(100), nullable=False)
    url = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    emailed = Column(String(10), default='no')  # 'yes' or 'no'
    emailed_date = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Job(job_id='{self.job_id}', title='{self.title}', source='{self.source}')>"


class Database:
    """Database manager for job listings"""
    
    def __init__(self, db_path=None):
        db_path = db_path or config.DATABASE_PATH
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def job_exists(self, job_id):
        """Check if a job with the given job_id already exists"""
        return self.session.query(Job).filter_by(job_id=job_id).first() is not None
    
    def add_job(self, job_data):
        """Add a new job to the database"""
        if self.job_exists(job_data['job_id']):
            return False
        
        job = Job(
            job_id=job_data['job_id'],
            title=job_data['title'],
            location=job_data.get('location'),
            description=job_data.get('description'),
            date_posted=job_data.get('date_posted'),
            source=job_data.get('source'),
            url=job_data.get('url')
        )
        
        self.session.add(job)
        self.session.commit()
        return True
    
    def get_new_jobs(self, since_date=None):
        """
        Get jobs that haven't been emailed yet
        
        Args:
            since_date: Only return jobs added to database after this date
                       (defaults to None - returns all unemailed jobs)
        
        Returns:
            List of Job objects that haven't been emailed
        """
        query = self.session.query(Job).filter_by(emailed='no')
        if since_date:
            # Filter by when job was added to database (created_at), not when it was posted
            query = query.filter(Job.created_at >= since_date)
        return query.all()
    
    def get_today_new_jobs(self):
        """
        Get jobs that were added to the database today and haven't been emailed yet.
        This ensures only newly scraped jobs from today's run are returned.
        """
        from datetime import datetime
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_new_jobs(since_date=today_start)
    
    def mark_as_emailed(self, job_ids):
        """Mark jobs as emailed"""
        jobs = self.session.query(Job).filter(Job.job_id.in_(job_ids)).all()
        for job in jobs:
            job.emailed = 'yes'
            job.emailed_date = datetime.utcnow()
        self.session.commit()
    
    def close(self):
        """Close the database session"""
        self.session.close()

