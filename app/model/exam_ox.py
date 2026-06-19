from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql.sqltypes import DATETIME_TIMEZONE

from app.db.mariadb import Base

class ExamOX(Base) :
    """
        DSDO의 "tb_ox_info"와 매핑
        정오표 게시판의 게시글 데이터
    """
    __tablename__ = "tb_ox_info"

    id = Column(Integer, primary_key=True, index=True )
    #   공개/비공개
    show_yn = Column(Text)
    #   공지 순서 (NOTICE_YN=''N''인 경우 NULL)
    gb=Column(String(50))
    #   게시글 구분값 코드(DSDO.TB_BBSGB_INFO)
    gb_cd=Column(Integer)

    #   제목
    title=Column(String(500))
    #   저장된 첨부파일 이름
    file=Column(String(100))
    #   원본 첨부파일 이름
    file_name=Column(String(100))

    #   조회수
    count=Column(Integer)
    reg_dt =Column(DATETIME_TIMEZONE)
