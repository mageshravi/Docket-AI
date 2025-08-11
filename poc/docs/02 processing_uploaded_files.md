# Processing Uploaded Files

This document outlines the solution design for processing uploaded files other than emails (EML files).

1. User uploads files. Allowed file types - PDF, DOCX, XLSX, PPTX, TXT, CSV and EML.
1. Uploaded file is saved to disk and a new record is created in `poc_uploaded_files` table (`UploadedFile` model).
1. The `UploadedFile` instance is then added to the `process_uploaded_file` queue.

## Process Uploaded File Worker

1. The worker processes one `UploadedFile` instance at a time.
1. The worker does the following,
    - check if the uploaded file exists.
    - check the file's status.
    - check if the uploaded file format is one of PDF, DOCX, XLSX, PPTX, TXT or CSV.
    - parse text content from the uploaded file.
    - split the text content into smaller chunks if necessary.
    - vectorize and create embeddings.
    - save the chunks + embeddings into the database table `poc_uploaded_file_embeddings` (`UploadedFileEmbedding` model).
