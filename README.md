# Exhibit AI

(Previously Docket AI)

Turn your case documents into visual timelines in minutes. Ask questions. Uncover key insights.

## Who is it for?

1. **Lawyers and law firms**<br>
Streamline case preparation by organizing files into timelines and querying case details instantly.
1. **Individuals involved in legal disputes**<br>
Easily recall events, dates, and facts — especially useful during cross-examinations or discussions with your lawyer.

## How it works

1. **Upload your proof documents** – Just drag and drop emails, PDFs, Word files, spreadsheets, images, and more.
1. **See a clear timeline** – All key events are automatically arranged in chronological order.
1. **Ask questions, get answers** – Chat with the built-in AI to understand the case, clarify facts, and spot insights.

## Running the application locally

### Requirements

1. Docker
1. docker-compose

### Steps

```bash
# clone the repo, then change working directory
cd Docket-AI

# create the .env file
cp .env.local .env

# build the container image
docker-compose build

# create and start containers in background mode
docker-compose up -d

# run database migrations and create superuser
docker-compose exec docket_ai-django ./_init_alpha.sh
```

Login into the application using the Django admin panel at http://localhost:8000/admin/.

### Running tests

```bash
# bash into the container
docker-compose exec docket_ai-django bash

cd ~/code

# option 1: without coverage report
pytest

# option 2: with coverage report
pytest --cov=.
```
