from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session
from app.db.mariadb import SessionLocal
from app.model.notice import Notice
from app.model.faq import Faq
from app.model.exam_ox import ExamOX
from app.model.ipsi import Ipsi

class DBService:
    def __init__(self, db: Session = None):
        self.db = db

    @contextmanager
    def get_session(self):
        if self.db:
            yield self.db
        else:
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()

    def get_notices(self):
        with self.get_session() as session:
            current_year = datetime.now().year
            start_of_year = datetime(current_year, 1, 1)
            return session.query(Notice).filter(
                Notice.show_yn == 'Y',
                Notice.edt_dt >= start_of_year
            ).all()

    def get_faqs(self):
        with self.get_session() as session:
            return session.query(Faq).filter(Faq.show_yn == 'Y').all()

    def get_exam_oxs(self):
        with self.get_session() as session:
            return session.query(ExamOX).filter(ExamOX.show_yn == 'Y').all()
        
    def get_ipsis(self):
        with self.get_session() as session:
            current_year = datetime.now().year
            start_of_year = datetime(current_year, 1, 1)
            return session.query(Ipsi).filter(
                Ipsi.open_yn == 'Y',
                Ipsi.mod_date >= start_of_year
            ).all()
