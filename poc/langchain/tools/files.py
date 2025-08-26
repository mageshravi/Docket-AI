from enum import Enum

from django.db.models import Q
from langchain.schema import Document
from langchain_core.tools import BaseTool
from pgvector.django.functions import CosineDistance
from pydantic import BaseModel

from poc.models import (
    ParsedEmailAttachment,
    ParsedEmailAttachmentEmbedding,
    UploadedFile,
    UploadedFileEmbedding,
)
from poc.utils import create_vector_embedding

__all__ = [
    "SearchByFilename",
    "SearchByFileType",
    "SemanticFileSearch",
]


def _transform_uploaded_files(uploaded_files: list[UploadedFile]) -> list:
    """
    Transform a list of UploadedFile objects into a list of Document objects.
    """
    documents = []
    for uploaded_file in uploaded_files:
        content = f"File: {uploaded_file.file.name}\nContent:\n"
        embeddings = uploaded_file.uploaded_file_embeddings.all()
        for embedding in embeddings:
            content += f"{embedding.chunk}\n"

        source = (
            "Type: Uploaded File",
            f"Filename: {uploaded_file.file.name}\n"
            f"File path: {uploaded_file.file.path}\n",
        )
        documents.append(
            {
                "content": content,
                "source": source,
            }
        )

    return documents


def _transform_email_attachments(
    email_attachments: list[ParsedEmailAttachment],
) -> list:
    """
    Transform a list of ParsedEmailAttachment objects into a list of Document objects.
    """
    documents = []
    for attachment in email_attachments:
        embeddings = attachment.parsed_email_attachment_embeddings.all()
        content = f"Filename: {attachment.filename}\nContent:\n"
        for embedding in embeddings:
            content += f"{embedding.chunk}\n"

        source = (
            "Type: Email attachment",
            f"Filename: {attachment.filename}\n"
            f"Email Subject: {attachment.parsed_email.subject}\n"
            f"Email From: {attachment.parsed_email.sender}\n"
            f"Email Sent on: {attachment.parsed_email.sent_on}\n",
        )

        documents.append(
            {
                "content": content,
                "source": source,
            }
        )

    return documents


class SearchByFilename(BaseTool):
    name: str = "search_file_by_name"
    description: str = "Search for a file by its name. Returns a list of file content and metadata about the source."

    def _run(self, filename: str) -> list[Document]:
        words = filename.split(" ")

        query = Q()
        for word in words:
            query |= Q(file__icontains=word)

        results = []

        uploaded_files = UploadedFile.objects.filter(query)
        results.extend(_transform_uploaded_files(uploaded_files))

        email_attachments = ParsedEmailAttachment.objects.filter(query)
        results.extend(_transform_email_attachments(email_attachments))

        return results


class FileType(str, Enum):
    document = "document"
    spreadsheet = "spreadsheet"
    presentation = "presentation"
    email = "email"


class FileTypeInput(BaseModel):
    file_type: FileType


class SearchByFileType(BaseTool):
    name: str = "search_file_by_type"
    description: str = "Search for files by their type (document, spreadsheet, presentation, email). Returns a list of file content and metadata about the source."
    args_schema: type[BaseModel] = FileTypeInput

    def _run(self, file_type: FileType) -> list[Document]:
        content_types = []
        extensions = []
        if file_type == FileType.email:
            content_types = [
                "message/rfc822",  # for EML files
            ]
            extensions = [".eml"]
        elif file_type == FileType.presentation:
            content_types = [
                "application/vnd.ms-powerpoint",  # for PPT files
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # for PPTX files
            ]
            extensions = [".ppt", ".pptx"]
        elif file_type == FileType.spreadsheet:
            content_types = [
                "application/vnd.ms-excel",  # for XLS files
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # for XLSX files
                "text/csv",  # for CSV files
            ]
            extensions = [".xls", ".xlsx", ".csv"]
        elif file_type == FileType.document:
            content_types = [
                "application/pdf",  # for PDF files
                "application/msword",  # for DOC files
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # for DOCX files
                "text/plain",  # for TXT files
            ]
            extensions = [".pdf", ".doc", ".docx", ".txt"]

        results = []

        if extensions:
            uf_query = Q()
            for ext in extensions:
                uf_query |= Q(file__iendswith=ext)

            uploaded_files = UploadedFile.objects.filter(uf_query)
            results.extend(_transform_uploaded_files(uploaded_files))

        if content_types:
            email_attachments = ParsedEmailAttachment.objects.filter(
                content_type__in=content_types
            )
            results.extend(_transform_email_attachments(email_attachments))

        return results


class SemanticFileSearch(BaseTool):
    name: str = "semantic_file_search"
    description: str = "Search case files using semantic search. Returns a list of relevant documents including metadata about the source."

    def _run(self, query: str, top_k: int = 5) -> list[Document]:
        query = create_vector_embedding([query])[0]["embedding"]
        docs = []

        file_chunks = UploadedFileEmbedding.objects.annotate(
            distance=CosineDistance("embedding", query)
        ).order_by("distance")[:top_k]

        # adding to a set to remove duplicates
        uploaded_files_set = {chunk.uploaded_file for chunk in file_chunks}
        uploaded_files = list(uploaded_files_set)
        docs.extend(_transform_uploaded_files(uploaded_files))

        attachment_chunks = ParsedEmailAttachmentEmbedding.objects.annotate(
            distance=CosineDistance("embedding", query)
        ).order_by("distance")[:top_k]

        email_attachments_set = {
            chunk.parsed_email_attachment for chunk in attachment_chunks
        }
        email_attachments = list(email_attachments_set)
        docs.extend(_transform_email_attachments(email_attachments))

        return docs
