from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT

from app.db.mariadb import Base

class Faq(Base) :
    """
        DSDO의 "tb_faq_info"와 매핑
        자주하는 질문 게시판의 게시글 데이터
    """
    __tablename__ = "tb_faq_info"

    id = Column(Integer, primary_key=True, index=True )
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
