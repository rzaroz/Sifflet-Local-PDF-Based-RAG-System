<p align="center">
  <img src="assets/logo.png" alt="Sifflet Logo" width="180">
</p>

# Sifflet – Local PDF-Based RAG System

Sifflet is a lightweight, locally operated Retrieval-Augmented Generation (RAG) application designed to transform PDF documents into searchable knowledge databases and enable context-aware question answering using Large Language Models (LLMs).

The application uses embedding models to convert document content into vector representations. When a user submits a question, the retrieval system performs semantic search to identify the most relevant passages based on their meaning rather than exact keyword matching.

The retrieved information is then incorporated into a prompt and provided to a locally loaded LLM through the Llama inference framework to generate context-aware responses.

## Features

- **PDF-Based Knowledge Extraction:** Convert PDF documents into searchable knowledge databases.
- **Semantic Search:** Retrieve relevant content using embedding models and vector similarity.
- **Local LLM Inference:** Run language models locally using the Llama framework.
- **Context-Aware Responses:** Provide retrieved document content as context for LLM-generated answers.
- **Offline Operation:** Designed to operate locally without requiring cloud-based AI services.
- **Customizable Retrieval:** Adjust the number of retrieved results according to your requirements.

## Language Support

The application's default interface language is currently **Persian (Farsi)**.

Users are free to modify the application's source code and localization resources to translate the interface into other languages or implement their own language support.

## Supported File Formats and Limitations

Currently, Sifflet supports PDF documents only. Other document formats are not supported by default, but additional format handlers can be implemented and integrated into the project.

**Important limitations:**

- PDF documents must contain machine-readable text.
- Scanned documents and PDFs containing text exclusively as page images are not supported.
- The application currently does not include Optical Character Recognition (OCR) capabilities.

To support scanned documents, an OCR engine must be integrated into the document extraction pipeline.

## Configuration

### Adjusting Retrieval Results

You can customize the number of retrieved document segments by modifying the `top_k` parameter in `retriever.py`.

Locate the following function:

```python
def search(cls, database, question, top_k=3):
```

Change the default value of `top_k` to control how many relevant document segments are retrieved and passed to the language model.

A higher value may provide more context but can also increase prompt length and inference time.

## Installation and Setup

Follow these steps to configure and run the application.

### 1. Configure the Llama Runtime

Download the appropriate version of the Llama runtime required by the application.

Extract the downloaded files and place their contents inside the project's `llama` directory.

Ensure that the runtime binaries and their required dependencies are available in the expected directory structure.

### 2. Configure the Embedding Model

Download or export your embedding model in ONNX format.

Place the following files inside the project's `embedder` directory:

```text
embedder/
├── model.onnx
└── tokenizer.json
```

Make sure the ONNX model and tokenizer belong to the same embedding model and are compatible with the application's inference pipeline.

### 3. Install Dependencies

Create and activate a Python virtual environment, then install the required dependencies:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

After configuring the Llama runtime, embedding model, and Python dependencies, launch the application using its main entry point.

```bash
python sifflet.py
```

## License

Sifflet is an open-source project.

The license currently included in the repository is provided for demonstration purposes only and should not be considered the project's final licensing terms.

Users and contributors should refer to the repository's license file for the applicable terms of use and distribution.

## Contributing

Contributions are welcome!

You can improve the project by:

- Adding support for additional document formats.
- Integrating OCR for scanned PDF documents.
- Improving document retrieval and embedding pipelines.
- Supporting additional embedding models and LLM backends.
- Optimizing local inference and memory consumption.
- Adding new interface languages and localization support.

Feel free to fork the repository, experiment with the code, and submit improvements.