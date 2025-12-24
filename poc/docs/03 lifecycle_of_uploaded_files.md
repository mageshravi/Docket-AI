# Lifecycle of Uploaded files

1. Uploaded files are owned by the user that uploaded them.
1. Any user with access to the case can edit the uploaded file (add or remove exhibit code).
1. Only the owner can delete an uploaded file. When a file is deleted,
    * the file is removed from the filesystem.
    * the file's embeddings are deleted.
    * but the file's entry in the UploadedFile table remains with the flag DELETED.

Note, deleted files are ignored from searches.

Maintain an audit log for all file operations i.e., create, edit and delete.
