from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT

from app.db.mariadb import Base

class Notice(Base) :
    """
        DSDO의 "tb_notice_info"와 매핑
        공지사항 게시판의 게시글 데이터
    """
    __tablename__ = "tb_notice_info"

    id = Column(Integer, primary_key=True, index=True )

    #   공지 설정 Y/N
    notice_yn = Column(Text)
    #   공개/비공개
    show_yn = Column(Text)
    #   공지 순서 (NOTICE_YN=''N''인 경우 NULL)
    ord=Column(Integer)
    #   (삭제 예정)게시글 구분값
    gb=Column(String(50))
    #   게시글 구분값 코드(DSDO.TB_BBSGB_INFO)
    gb_cd=Column(Integer)

    #   제목
    title=Column(String(500))
    #   텍스트 내용
    body=Column(LONGTEXT)
    #   조회수
    count=Column(Integer)
    #   저장된 첨부파일 이름
    file=Column(String(100))
    #   원본 첨부파일 이름
    file_name=Column(String(100))
    #   저장된 PDF 파일 이름
    pdf_file=Column(String(100))
    #   원본 PDF 파일 이름
    pdf_name=Column(String(100))

    edt_dt = Column(DateTime)
