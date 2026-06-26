# LLM-Powered C++ Code Modernizer

An automated tool that detects deprecated C++ patterns using AST parsing 
and modernizes them to C++17 standards using LLM prompt chaining.

## What it does
- Parses C++ files using libclang to build an Abstract Syntax Tree
- Detects deprecated patterns: raw pointers, C-style casts, NULL usage
- Sends each issue through a 3-stage LLM prompt chain (explain → fix → review)
- Validates the modernized code compiles successfully with g++

## Example
**Before (legacy C++):**
```cpp
int* arr = new int[size];   // raw pointer
int x = (int)val;           // C-style cast
if (ptr == NULL) { ... }    // NULL
```

**After (modern C++17):**
```cpp
auto arr = std::make_unique<int[]>(size);  // smart pointer
int x = static_cast<int>(val);            // safe cast
if (!ptr) { ... }                         // modern null check
```

## Tech Stack
- Python 3
- libclang (AST parsing)
- Groq API / LLaMA 3.3 70B (LLM prompt chaining)
- g++ (compile-time validation)

## Setup
```bash
git clone https://github.com/YOURUSERNAME/cpp-modernizer
cd cpp-modernizer
python3 -m venv venv
source venv/bin/activate
pip install openai python-dotenv clang groq
```

Add your Groq API key to `.env`:

GROQ_API_KEY=your_key_here

## Run
```bash
python3 main.py
```