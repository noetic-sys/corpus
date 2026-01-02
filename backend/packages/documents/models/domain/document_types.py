from __future__ import annotations
from enum import Enum
from typing import List, Set, Optional
from dataclasses import dataclass


class ExtractorType(str, Enum):
    """Enum for document extractor types."""

    GEMINI = "gemini"
    PASSTHROUGH = "passthrough"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    AUDIO = "audio"


@dataclass(frozen=True)
class DocumentTypeInfo:
    """Metadata for a document type."""

    extensions: List[str]  # ['.pdf', '.PDF']
    mime_types: List[str]  # ['application/pdf']
    is_extractable: bool  # Can we extract content?
    extractor_type: ExtractorType  # Type-safe extractor reference
    category: str  # 'document', 'image', 'audio', 'spreadsheet'
    display_name: str  # 'PDF Document'
    max_file_size_mb: int = 10  # Default 10MB limit


class DocumentType(Enum):
    """Centralized document type definitions with complete metadata."""

    # PDF Documents
    PDF = DocumentTypeInfo(
        extensions=[".pdf"],
        mime_types=["application/pdf"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="document",
        display_name="PDF Document",
    )

    # Text Documents
    TXT = DocumentTypeInfo(
        extensions=[".txt"],
        mime_types=["text/plain"],
        is_extractable=True,
        extractor_type=ExtractorType.PASSTHROUGH,
        category="document",
        display_name="Text File",
    )

    MARKDOWN = DocumentTypeInfo(
        extensions=[".md"],
        mime_types=["text/markdown"],
        is_extractable=True,
        extractor_type=ExtractorType.PASSTHROUGH,
        category="document",
        display_name="Markdown File",
    )

    # Microsoft Word Documents
    WORD_DOC = DocumentTypeInfo(
        extensions=[".doc"],
        mime_types=["application/msword"],
        is_extractable=True,
        extractor_type=ExtractorType.WORD,
        category="document",
        display_name="Word Document (Legacy)",
    )

    WORD_DOCX = DocumentTypeInfo(
        extensions=[".docx"],
        mime_types=[
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        is_extractable=True,
        extractor_type=ExtractorType.WORD,
        category="document",
        display_name="Word Document",
    )

    # Microsoft Excel Spreadsheets
    EXCEL_XLS = DocumentTypeInfo(
        extensions=[".xls"],
        mime_types=["application/vnd.ms-excel"],
        is_extractable=True,
        extractor_type=ExtractorType.EXCEL,
        category="spreadsheet",
        display_name="Excel Spreadsheet (Legacy)",
    )

    EXCEL_XLSX = DocumentTypeInfo(
        extensions=[".xlsx"],
        mime_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ],
        is_extractable=True,
        extractor_type=ExtractorType.EXCEL,
        category="spreadsheet",
        display_name="Excel Spreadsheet",
    )

    # CSV
    CSV = DocumentTypeInfo(
        extensions=[".csv"],
        mime_types=["text/csv"],
        is_extractable=True,
        extractor_type=ExtractorType.EXCEL,
        category="spreadsheet",
        display_name="CSV File",
    )

    # Microsoft PowerPoint Presentations
    POWERPOINT_PPT = DocumentTypeInfo(
        extensions=[".ppt"],
        mime_types=["application/vnd.ms-powerpoint"],
        is_extractable=True,
        extractor_type=ExtractorType.POWERPOINT,
        category="presentation",
        display_name="PowerPoint Presentation (Legacy)",
    )

    POWERPOINT_PPTX = DocumentTypeInfo(
        extensions=[".pptx"],
        mime_types=[
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ],
        is_extractable=True,
        extractor_type=ExtractorType.POWERPOINT,
        category="presentation",
        display_name="PowerPoint Presentation",
    )

    # Image Files
    JPEG = DocumentTypeInfo(
        extensions=[".jpg", ".jpeg"],
        mime_types=["image/jpeg"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="JPEG Image",
    )

    PNG = DocumentTypeInfo(
        extensions=[".png"],
        mime_types=["image/png"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="PNG Image",
    )

    GIF = DocumentTypeInfo(
        extensions=[".gif"],
        mime_types=["image/gif"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="GIF Image",
    )

    BMP = DocumentTypeInfo(
        extensions=[".bmp"],
        mime_types=["image/bmp"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="BMP Image",
    )

    TIFF = DocumentTypeInfo(
        extensions=[".tiff", ".tif"],
        mime_types=["image/tiff"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="TIFF Image",
    )

    WEBP = DocumentTypeInfo(
        extensions=[".webp"],
        mime_types=["image/webp"],
        is_extractable=True,
        extractor_type=ExtractorType.GEMINI,
        category="image",
        display_name="WebP Image",
    )

    # Audio Files
    MP3 = DocumentTypeInfo(
        extensions=[".mp3"],
        mime_types=["audio/mpeg", "audio/mp3"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="MP3 Audio",
    )

    WAV = DocumentTypeInfo(
        extensions=[".wav"],
        mime_types=["audio/wav"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="WAV Audio",
    )

    FLAC = DocumentTypeInfo(
        extensions=[".flac"],
        mime_types=["audio/flac"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="FLAC Audio",
    )

    OGG = DocumentTypeInfo(
        extensions=[".ogg"],
        mime_types=["audio/ogg"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="OGG Audio",
    )

    WEBM = DocumentTypeInfo(
        extensions=[".webm"],
        mime_types=["audio/webm"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="WebM Audio",
    )

    M4A = DocumentTypeInfo(
        extensions=[".m4a"],
        mime_types=["audio/mp4", "audio/m4a"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="M4A Audio",
    )

    AAC = DocumentTypeInfo(
        extensions=[".aac"],
        mime_types=["audio/aac"],
        is_extractable=True,
        extractor_type=ExtractorType.AUDIO,
        category="audio",
        display_name="AAC Audio",
    )

    @classmethod
    def get_all_extensions(cls) -> List[str]:
        """Get all supported file extensions (lowercase)."""
        extensions = []
        for doc_type in cls:
            extensions.extend([ext.lower() for ext in doc_type.value.extensions])
        return sorted(list(set(extensions)))

    @classmethod
    def get_all_mime_types(cls) -> List[str]:
        """Get all supported MIME types."""
        mime_types = []
        for doc_type in cls:
            mime_types.extend(doc_type.value.mime_types)
        return sorted(list(set(mime_types)))

    @classmethod
    def get_extractable_types(cls) -> Set["DocumentType"]:
        """Get all extractable document types."""
        return {dt for dt in cls if dt.value.is_extractable}

    @classmethod
    def get_extractable_extensions(cls) -> List[str]:
        """Get file extensions for extractable document types."""
        extensions = []
        for doc_type in cls.get_extractable_types():
            extensions.extend([ext.lower() for ext in doc_type.value.extensions])
        return sorted(list(set(extensions)))

    @classmethod
    def get_extractable_mime_types(cls) -> Set[str]:
        """Get MIME types for extractable document types."""
        mime_types = set()
        for doc_type in cls.get_extractable_types():
            mime_types.update(doc_type.value.mime_types)
        return mime_types

    @classmethod
    def from_extension(cls, ext: str) -> Optional["DocumentType"]:
        """Find document type by file extension."""
        ext_lower = ext.lower()
        if not ext_lower.startswith("."):
            ext_lower = f".{ext_lower}"

        for doc_type in cls:
            if ext_lower in [e.lower() for e in doc_type.value.extensions]:
                return doc_type
        return None

    @classmethod
    def from_mime_type(cls, mime: str) -> Optional["DocumentType"]:
        """Find document type by MIME type."""
        mime_lower = mime.lower()
        for doc_type in cls:
            if mime_lower in [m.lower() for m in doc_type.value.mime_types]:
                return doc_type
        return None

    @classmethod
    def from_filename(cls, filename: str) -> Optional["DocumentType"]:
        """Find document type by filename."""
        if "." not in filename:
            return None
        ext = "." + filename.split(".")[-1].lower()
        return cls.from_extension(ext)

    @classmethod
    def get_type_mapping(cls) -> dict[str, str]:
        """Get mapping from content type to file type for backwards compatibility."""
        mapping = {}
        for doc_type in cls:
            for mime_type in doc_type.value.mime_types:
                # Use the first extension as the canonical file type
                if doc_type.value.extensions:
                    file_type = doc_type.value.extensions[0][1:]  # Remove the dot
                    mapping[mime_type] = file_type
        return mapping

    @classmethod
    def get_types_by_category(cls, category: str) -> List["DocumentType"]:
        """Get all document types in a specific category."""
        return [dt for dt in cls if dt.value.category == category]
