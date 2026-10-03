# 🧠 B.Tech Brain — Personal RAG Knowledge System

A personal Retrieval-Augmented Generation (RAG) system built to turn a large collection of B.Tech course material into a searchable, question-answering knowledge base.

The system processes textbooks, lecture notes, scanned PDFs, assignments, and other academic material using PDF extraction, OCR, semantic embeddings, hybrid retrieval, FAISS, TF-IDF, and Gemini.

---
      B.Tech Course Material
                             │
                             ▼
                  PDF Extraction + OCR
                             │
                             ▼
                       Text Cleaning
                             │
                             ▼
                    Page-level Corpus
                             │
                             ▼
                         Chunking
                             │
                             ▼
                  Sentence Embeddings
                             │
                             ▼
                       FAISS Index
                             │
                             ├──────────────┐
                             ▼              ▼
                    Semantic Search    TF-IDF Search
                             │              │
                             └──────┬───────┘
                                    ▼
                            Hybrid Retrieval
                                    │
                                    ▼
                              Top-K Context
                                    │
                                    ▼
                              Gemini LLM
                                    │
                                    ▼
                         Grounded Answer
                                    │
                                    ▼
                              Source Pages

## ✨ Overview

**B.Tech Brain** is designed to answer technical questions from a personal academic corpus rather than relying entirely on a general-purpose LLM.

Instead of sending a question directly to an LLM, the system follows above pipeline:

## 🚀 Features 
### 📚 Large Academic Corpus

The system was developed around a personal B.Tech corpus containing:

7,312 files
520 PDFs
32,519 PDF pages
Multiple semesters and courses
Textbooks
Lecture notes
Reference books
Assignments
Course material
Scanned documents


## 🔍 PDF Text Extraction

PDFs are processed using pypdf.

Native PDF text is preserved whenever available.

This is important because many academic PDFs contain useful text that should not be replaced by OCR.

## 👁️ OCR for Scanned PDFs

Scanned and image-heavy PDF pages are processed using:

PyMuPDF
Tesseract OCR
300 DPI rendering

OCR is only used when native PDF text is unavailable or insufficient.

The pipeline keeps native text and OCR text logically separate to avoid unnecessarily replacing good PDF text with noisy OCR output.

## 🧹 Corpus Cleaning

The OCR pipeline includes quality checks to avoid inserting obviously bad OCR results into the final corpus.

The cleaning stage checks things such as:

minimum text length
alphanumeric ratio
suspicious OCR output
empty pages
extremely short OCR results

This produces a cleaner corpus before retrieval.

## ✂️ Page-Aware Chunking

The cleaned corpus is converted into retrieval chunks.

The chunking pipeline uses:

paragraph-aware splitting
word-based chunk sizing
overlap between chunks
maximum page span per chunk

The current corpus contains approximately:

31,057 pages
14,296 chunks

A maximum page span is used to prevent slide-heavy or sparse documents from producing huge chunks covering unrelated sections.

## 🧠 Semantic Search

The project uses:

sentence-transformers/all-MiniLM-L6-v2

to generate dense vector embeddings.

Embedding dimension:

384

The embeddings are normalized and stored in a FAISS index.

Current index size:

14,296 vectors

## 🔎 Hybrid Retrieval

Pure semantic search can sometimes miss exact technical terminology.

For example, a query containing a specific scientific term may benefit from exact keyword matching.

B.Tech Brain therefore combines:

Semantic Retrieval

Using:

FAISS + MiniLM embeddings
Keyword Retrieval

Using:

TF-IDF

## 🔍 Retrieval Pipeline

```text
                Query
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   FAISS Search         TF-IDF Search
        │                   │
        └─────────┬─────────┘
                  ▼
            Score Fusion
                  │
                  ▼
          Duplicate Filtering
                  │
                  ▼
             Top Results
```

Your content below this point will render as normal Markdown.

## 🤖 RAG Chat

Add your RAG Chat content here.

Current hybrid weighting:

Semantic retrieval: 65%
Keyword retrieval:  35%

These weights are configurable.

## 🤖 LLM Generation

Retrieved context is passed to Gemini for answer generation.

The LLM is instructed to:

use the retrieved knowledge base
avoid inventing unsupported information
explicitly state when retrieved information is insufficient
explain technical concepts clearly
cite retrieved sources

The LLM therefore acts primarily as the answer-generation and reasoning layer, while retrieval determines what academic material it can use.

## 📖 Source Grounding

Answers include references to retrieved source material.

For example:

[SOURCE 1]
[SOURCE 2]
[SOURCE 3]

The CLI also displays:

source file
page range
hybrid score
semantic similarity score
keyword similarity score

This makes it possible to inspect why a particular chunk was retrieved.

## 🏗️ Project Structure

```text
my_btech_brain/
│
├── rag_chat.py
├── build_keyword_index.py
├── build_embeddings.py
├── chunk_corpus.py
├── build_clean_corpus.py
├── extract_pdfs.py
├── ocr_pdfs.py
├── render_highres.py
├── document_profiler.py
├── inspect_clean_corpus.py
├── validate_chunks.py
├── test_retrieval.py
│
├── processed/
│   │
│   ├── clean/
│   │   ├── clean_pages.jsonl
│   │   ├── rejected_pages.jsonl
│   │   └── clean_corpus_stats.json
│   │
│   ├── chunks/
│   │   ├── chunks.jsonl
│   │   └── chunk_stats.json
│   │
│   ├── embeddings/
│   │   ├── index.faiss
│   │   ├── metadata.jsonl
│   │   └── embedding_stats.json
│   │
│   ├── keyword_index/
│   │   ├── tfidf_vectorizer.pkl
│   │   ├── tfidf_matrix.pkl
│   │   └── metadata.jsonl
│   │
│   └── ocr/
│       ├── pdf_pages_ocr.jsonl
│       └── ocr_errors.jsonl
│
└── README.md
```

The original academic corpus is kept outside the Git repository.

## ⚙️ Technology Stack

Your technology stack content goes here normally.

### 🔧 Installation

Your installation content goes here normally.

### 🚀 Usage

Your usage content goes here normally.

The original academic corpus is kept outside the Git repository.

## ⚙️ Technology Stack
Component	Technology
Language	Python
PDF extraction	pypdf
PDF rendering	PyMuPDF
OCR	Tesseract
OCR integration	pytesseract
Embeddings	Sentence Transformers
Embedding model	all-MiniLM-L6-v2
Vector database	FAISS
Keyword retrieval	scikit-learn TF-IDF
LLM	Google Gemini
Environment	Python virtual environment
Development	VS Code

## 📊 Current Pipeline Statistics

The current processed corpus contains approximately:

Source files              519
Processed pages           31,057
Accepted characters       57M+
Chunks                    14,296
Embedding dimension       384
FAISS vectors             14,296

The PDF processing stage originally handled:

520 PDFs
32,519 pages

The difference between raw PDF pages and accepted clean pages is intentional: some pages contain no useful extractable content or failed quality checks.

## 🛠️ Installation
1. Clone the repository
git clone https://github.com/<your-username>/my_btech_brain.git
cd my_btech_brain
2. Create a virtual environment

Windows:

python -m venv .venv

Activate it:

.venv\Scripts\Activate.ps1
3. Install dependencies

Install the required Python packages:

pip install pypdf
pip install Pillow
pip install PyMuPDF
pip install pytesseract
pip install sentence-transformers
pip install faiss-cpu
pip install google-genai
pip install scikit-learn


## 🔑 API Key Configuration

The project uses the Gemini API for answer generation.

Set your API key as an environment variable.

PowerShell:

$env:GEMINI_API_KEY="YOUR_API_KEY"

Verify:

python -c "import os; print(bool(os.getenv('GEMINI_API_KEY')))"

Expected:

True
Important

Never commit API keys to GitHub.

Do not put the key directly inside Python source code.

Add .env, secrets, and local configuration files to .gitignore.

## 👁️ Tesseract Installation

OCR requires Tesseract.

On Windows, install Tesseract and make sure the executable is available.

Example path:

C:\Program Files\Tesseract-OCR\tesseract.exe

The OCR scripts can explicitly configure the executable path.

## 📥 Adding Your Own Corpus

The original project uses an external course directory.

```text
courses/
├── CHE221/
├── CHE311/
├── CHE352/
├── GenAI/
├── ESO201/
└── ...
```
You can replace this with your own academic corpus.

The corpus itself is intentionally not included in this repository because it may contain copyrighted textbooks and personal academic material.

## 🔄 Building the Pipeline

The general processing sequence is:

1. Inventory and profile documents
python document_profiler.py
2. Extract PDF text
python extract_pdfs.py
3. Run OCR
python ocr_pdfs.py
4. Build the clean corpus
python build_clean_corpus.py
5. Create chunks
python chunk_corpus.py
6. Build embeddings
python build_embeddings.py
7. Build keyword index
python build_keyword_index.py
8. Start the RAG system
python rag_chat.py


## 💬 Example
### B.Tech Brain - Hybrid RAG
=================================================================

B.Tech Brain is ready.
Type 'exit' to quit.

You > What is the first law of thermodynamics?

The system retrieves relevant thermodynamics material and generates a grounded response using the retrieved context.

## 🧪 Retrieval Testing

The project includes retrieval testing to inspect the quality of semantic search.

Example:

python test_retrieval.py

Questions can be tested against the FAISS index to determine whether relevant academic material appears among the retrieved results.

## 🎯 Design Goals

The project is designed around several principles.

1. Retrieval before generation

The LLM should not be the only source of knowledge.

Relevant material should first be retrieved from the user's own corpus.

2. Grounded answers

The model should prefer information present in retrieved documents.

3. Source traceability

Answers should be traceable back to academic source files and page ranges.

4. Local control of the knowledge base

The academic corpus remains under the user's control.

5. Modular architecture

Each stage can be improved independently:

Ingestion
   ↓
OCR
   ↓
Cleaning
   ↓
Chunking
   ↓
Embeddings
   ↓
Retrieval
   ↓
Reranking
   ↓
Generation


## 🚧 Current Limitations

This is an actively developed project and is not yet a production-grade knowledge system.

Current limitations include:

Retrieval can still return semantically related but non-optimal chunks.
TF-IDF and vector scores are currently combined using fixed weights.
A dedicated reranker has not yet been added.
Source metadata presentation is still being refined.
OCR quality depends on the original scan quality.
Some pages contain little or no useful text.
The LLM API can experience temporary service unavailability.
The current interface is CLI-based.
Conversation memory is limited.
There is currently no automated large-scale retrieval benchmark.
The corpus contains material with different document quality and structure.


## 🗺️ Roadmap
### ✅ Phase 1 — Knowledge ingestion
 PDF inventory
 PDF text extraction
 OCR
 OCR quality filtering
 Clean corpus
 Page-aware chunking
 
### ✅ Phase 2 — Basic RAG
 Sentence embeddings
 FAISS vector index
 Semantic retrieval
 Gemini integration
 Grounded answer generation
 
### 🚧 Phase 3 — Retrieval improvements
 TF-IDF keyword retrieval
 Hybrid retrieval
 Candidate expansion
 Duplicate suppression
 Retrieval reranker
 Query expansion
 Better technical-term matching
 Automatic retrieval evaluation

### 🔜 Phase 4 — Evaluation
 Build 50–100 benchmark questions
 Measure Recall@K
 Measure Precision@K
 Measure MRR
 Compare FAISS vs hybrid retrieval
 Tune retrieval weights
 Evaluate answer grounding
 
### 🔜 Phase 5 — User Experience
 Conversation history
 Follow-up questions
 Better source display
 Page-level document navigation
 Web interface
 Streamlit/Gradio interface

 
## 🔭 Future
 Cross-encoder reranking
 Better mathematical retrieval
 Table-aware extraction
 Image/diagram understanding
 Multimodal document retrieval
 Course-aware retrieval
 Semester/course filters
 Personal study analytics

 
## 🔐 Privacy

The academic corpus is intended to remain local.

The retrieval pipeline processes the documents locally:

PDF
 ↓
Extraction/OCR
 ↓
Cleaning
 ↓
Chunking
 ↓
Embeddings
 ↓
FAISS/TF-IDF

Only the selected retrieved context is sent to the configured LLM API for answer generation.

Users should review the privacy and data-handling policies of their chosen LLM provider before using sensitive documents.



## 👨‍💻 Author

Ajay Singh

B.Tech student building a personal AI-powered academic knowledge system.
```text

              
