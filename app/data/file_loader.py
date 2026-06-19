from abc import abstractmethod, ABC

from pathlib import Path
from typing import List, Dict

import pandas as pd

from app.core.logger import get_logger
from app.schemas.RawDocument import RawDocument

log = get_logger(__name__)

# PDF 지원 (선택적)
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class BaseLoader(ABC):
    @abstractmethod
    def load(self) -> List[RawDocument]:
        """각 소스에서 데이터를 읽어 RawDocument 리스트로 반환"""
        pass

    @abstractmethod
    def load_directory(self, dir_path: List[str | Path]) -> Dict[str, str]:
        """
        디렉토리 내 모든 지원 파일을 로드합니다.
        Args:
            dir_path: 대상 디렉토리
        Returns:
            Dict: {파일경로: 텍스트내용} 딕셔너리
        """
# ── 문서(.pdf, .txt) 로더 ─────────────────────────────────────────────────────────────────
class DocumentLoader(BaseLoader):
    """다양한 파일 포맷을 텍스트 문자열로 로드"""
    SUPPORTED_EXTENSIONS = {".txt", ".pdf"}

    def __init__(self, file_path: str | Path):
        self.file_path = file_path

    def load(self) -> List[str]:
        path = Path(self.file_path)
        suffix = path.suffix.lower()

        if suffix == ".txt":
            text = path.read_text(encoding="utf-8")
            return [line for line in text.splitlines() if line.strip()]

        elif suffix == ".pdf":
            if not HAS_PYPDF:
                raise ImportError(
                    "pypdf 패키지가 필요합니다: pip install pypdf"
                )
            reader = PdfReader(str(path))
            return [page.extract_text() or "" for page in reader.pages]

        else:
            raise ValueError(
                f"지원하지 않는 파일 형식: '{suffix}' "
                f"(지원: {', '.join(self.SUPPORTED_EXTENSIONS)})"
            )

    def load_directory(
            self,
            dir_path: str | Path,
    ) -> Dict[str, List[str]]:
        exts = list(self.SUPPORTED_EXTENSIONS)
        dir_path = Path(dir_path)
        result: Dict[str, List[str]] = {}

        for ext in exts:
            for file_path in sorted(dir_path.glob(f"*{ext}")):
                try:
                    result[str(file_path)] = self.load()
                    log.info(f"[DocumentLoader] 로드 완료: {file_path.name}")
                except Exception as e:
                    log.info(f"[DocumentLoader] 경고 - {file_path.name} 로드 실패: {e}")

        return result

# ── 엑셀 로더 ───────────────────────────────────────────────────────────────
class ExcelLoader(BaseLoader):
    """ xlsx -> txt"""
    SUPPORTED_EXTENSIONS = { ".xlsx", ".csv"}

    def __init__(self, file_path: str | Path, target_cols : List[str]  = None):
        self.file_path = file_path
        self.target_cols = target_cols

    def load(self, columns : List[str] = None) -> List[str]:
        path = Path(self.file_path)
        suffix = path.suffix.lower()
        columns = ["쇼핑몰", "상품명","표준카테고리","단축 URL","검색어",	"판매가"]
        if suffix == ".csv":
            df = pd.read_csv(self.file_path, encodings="utf-8")
        elif suffix == ".xlsx":
            df = pd.read_excel(self.file_path)
        else:
            raise ValueError(
                f"지원하지 않는 파일 형식: '{suffix}' "
                f"(지원: {', '.join(self.SUPPORTED_EXTENSIONS)})"
            )

        return self.dataframe_to_text(df, columns)

    def load_directory(
            self,
            dir_path: str | Path
    ) -> Dict[str, List[str]]:
        exts = list(self.SUPPORTED_EXTENSIONS)
        dir_path = Path(dir_path)
        result: Dict[str, List[str]] = {}

        for ext in exts:
            for file_path in sorted(dir_path.glob(f"*{ext}")):
                try:
                    result[str(file_path)] = self.load()
                    log.info(f"[DocumentLoader] 로드 완료: {file_path.name}")
                except Exception as e:
                    log.info(f"[DocumentLoader] 경고 - {file_path.name} 로드 실패: {e}")

        return result

    def dataframe_to_text(
            self, df: pd.DataFrame,
            columns: List[str]= None) -> List[str] :
        """
        DataFrame의 각 행(Row)을 단일 텍스트 파일로 변환하여 저장합니다.
        Args:
            df: 변환할 데이터가 저장된 pandas dataframe 객체
            columns: 유효한 컬럼명 목록
        Returns:
            None: 반환값 없이 지정된 경로에 파일들을 생성합니다.
        Raises:
            KeyError: `columns`에 지정된 컬럼이 DataFrame에 없을 경우 발생.
        """

        if not columns :
            columns = [col for col in df.columns]

        for col in columns :
            if col not in df.columns : raise  KeyError(f"내용으로 지정한 컬럼 '{col}이 데이터 내에 존재하지 않습니다.")

        content = df[columns].apply(lambda row: "상품정보 "+" ".join(row.dropna().astype(str)), axis=1).to_list()

        return content