# Processing Uploaded Emails

1. User uploads the EML files.
1. Create a new instance of the `UploadedFile` model and save. This should create a record in the `poc_uploaded_files` table and save the file to the disk.
1. Finally, add the `UploadedFile` model instance to the `process_email` job queue.

## Process Email Worker

1. The `process_email` workers process the `UploadedFile` instances one at a time.
1. They parse the following from the EML file:
    - meta data: date, sender and recipients)
    - content: subject, body and _cleaned body_ (striped of quoted replies)
    - attachments
1. The parsed data is used to create the `ParsedEmail` model instance.
1. If any attachment found, the worker creates an instance of the `ParsedEmailAttachment` model, and adds it to the `process_email_attachment` job queue.
1. Upon successfully parsing/saving the EML file contents to the database, the worker adds the file to `embed_email` job queue. This queue's workers create vector embeddings from the cleaned body and saves them to database.

## Process Email Attachment Worker

The `process_email_attachment` worker,

1. reads the contents of the attachment
1. chunks them into smaller bits
1. creates vector embeddings for the chunks
1. saves the chunks + embeddings in the database using the `ParsedEmailAttachmentEmbedding` model.

## Embed Email Worker

The `embed_email` worker,

1. reads the email's _cleaned body_ content
1. chunks into smaller bits if necessary
1. creates vector embeddings and
1. saves them to the database using the `ParsedEmailEmbedding` model.
