from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT

from app.db.mariadb import Base


class Ipsi(Base):
    """
        DSDO의 "tb_ipsi_info"와 매핑
        입시 자료 게시판의 게시글 데이터
    """
    __tablename__ = "tb_ipsi_info"
    b_no = Column(Integer, primary_key=True, index=True)
    #   '입시 정보 게시판 구분 - 입시뉴스/입시전략/대입보도자료',
    entexm_dstin = Column(String(50))
    #   '상단 공지 여부',
    top_noti_yn = Column(Integer)
    #   '제목',
    title = Column(String(1024))
    #   '내용',
    cont = Column(LONGTEXT)
    #   '공개 여부',
    open_yn = Column(Text)

    mod_date = Column(DateTime)
